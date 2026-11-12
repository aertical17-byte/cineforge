/**
 CineForge AI launcher — native macOS app (AppKit, no dependencies, no storyboards).

 What it does (Italian UI for non-technical users):
 1. Checks Docker + git and says so honestly.
 2. "Prepara e avvia" → asks for a folder, clones the public repo, runs docker compose,
    waits for http://localhost:3000, then opens the browser. First boot builds images
    (5-15 min) — the log area shows live progress so the user is never lost.
 3. "Apri l'app", "Ferma i servizi", bundled offline guide, GitHub link.

 Honesty rules (project principle): never fake success. If Docker is missing we say it;
 if compose fails we show the log; if the wait times out we say the containers may still
 be building instead of pretending the app is ready.
 */
import AppKit

let REPO_URL = "https://github.com/aertical17-byte/cineforge"
let REPO_LINK = URL(string: REPO_URL)!
let WEB_URL = URL(string: "http://127.0.0.1:3000/")!
let DOCKER_SITE = URL(string: "https://www.docker.com/products/docker-desktop/")!
let COMPOSE_CMD = "docker compose -f infra/docker/docker-compose.yml --project-directory . "

// MARK: - Small helpers

final class Box {
    var value = false
}

enum Log {
    static weak var view: NSTextView?
    static func append(_ s: String) {
        DispatchQueue.main.async {
            guard let tv = view else { return }
            let text = s.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !text.isEmpty else { return }
            if tv.textStorage?.length ?? 0 > 200_000 {  // keep long builds bounded
                tv.textStorage?.deleteCharacters(in: NSRange(location: 0, length: 100_000))
            }
            tv.textStorage?.append(NSAttributedString(
                string: text + "\n",
                attributes: [.font: NSFont.monospacedSystemFont(ofSize: 11, weight: .regular),
                             .foregroundColor: NSColor.secondaryLabelColor]))
            tv.scrollToEndOfDocument(nil)
        }
    }
}

enum Shell {
    /// Streams a command's output into the log, then calls onExit on the background queue.
    static func run(_ command: String, cwd: URL? = nil, onExit: @escaping (Int32) -> Void) {
        DispatchQueue.global(qos: .userInitiated).async {
            let p = Process()
            p.executableURL = URL(fileURLWithPath: "/bin/zsh")
            p.arguments = ["-lc", command]
            if let cwd { p.currentDirectoryURL = cwd }
            let out = Pipe(), err = Pipe()
            p.standardOutput = out
            p.standardError = err
            out.fileHandleForReading.readabilityHandler = { h in Log.append(String(data: h.availableData, encoding: .utf8) ?? "") }
            err.fileHandleForReading.readabilityHandler = { h in Log.append(String(data: h.availableData, encoding: .utf8) ?? "") }
            do { try p.run() } catch { Log.append("❌ \(error.localizedDescription)"); onExit(-1); return }
            p.waitUntilExit()
            out.fileHandleForReading.readabilityHandler = nil
            err.fileHandleForReading.readabilityHandler = nil
            onExit(p.terminationStatus)
        }
    }

    /// Synchronous probe for small checks (PATH resolution via a login shell).
    static func quick(_ command: String) -> Int32 {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/zsh")
        p.arguments = ["-lc", command]
        p.standardOutput = Pipe()
        p.standardError = Pipe()
        do { try p.run() } catch { return -1 }
        p.waitUntilExit()
        return p.terminationStatus
    }
}

enum Health {
    static func isUp() -> Bool {
        let box = Box()
        var req = URLRequest(url: WEB_URL)
        req.timeoutInterval = 3
        let sem = DispatchSemaphore(value: 0)
        URLSession.shared.dataTask(with: req) { _, resp, _ in
            box.value = (resp as? HTTPURLResponse)?.statusCode == 200
            sem.signal()
        }.resume()
        sem.wait()
        return box.value
    }
}

enum PickFolder {
    static var chosen: URL?
    /// Opens a folder picker on the main thread and blocks the caller (background queue).
    static func ask() -> URL? {
        let sem = DispatchSemaphore(value: 0)
        DispatchQueue.main.async {
            let panel = NSOpenPanel()
            panel.canChooseFiles = false
            panel.canChooseDirectories = true
            panel.allowsMultipleSelection = false
            panel.prompt = "Scegli cartella"
            panel.message = "Dove vuoi installare CineForge AI? Verrà creata una sottocartella «cineforge»."
            let code = panel.runModal()
            PickFolder.chosen = (code == .OK) ? panel.url : nil
            sem.signal()
        }
        sem.wait()
        return PickFolder.chosen
    }
}

// MARK: - App delegate

final class AppDelegate: NSObject, NSApplicationDelegate {
    static var shared: AppDelegate?

    var window: NSWindow!
    var dockerLabel: NSTextField!
    var gitLabel: NSTextField!
    var stateLabel: NSTextField!
    var primaryButton: NSButton!
    var openAppButton: NSButton!
    var stopButton: NSButton!
    var progress: NSProgressIndicator!
    var installDir: URL? {
        get { UserDefaults.standard.url(forKey: "installDir") }
        set { UserDefaults.standard.set(newValue, forKey: "installDir") }
    }
    let queue = DispatchQueue(label: "cineforge.launcher", qos: .userInitiated)

    func applicationDidFinishLaunching(_ note: Notification) {
        AppDelegate.shared = self
        buildUI()
        runSelfChecks()
    }

    // MARK: UI

    func label(_ text: String, size: CGFloat = 13, weight: NSFont.Weight = .regular,
               color: NSColor = NSColor.labelColor, center: Bool = false) -> NSTextField {
        let f = NSTextField(labelWithString: text)
        f.font = .systemFont(ofSize: size, weight: weight)
        f.textColor = color
        f.alignment = center ? .center : .left
        f.usesSingleLineMode = false
        f.lineBreakMode = .byWordWrapping
        return f
    }

    func button(_ title: String, _ sel: Selector, large: Bool = false) -> NSButton {
        let b = NSButton(title: title, target: self, action: sel)
        b.bezelStyle = .rounded
        b.controlSize = large ? .large : .regular
        b.font = .systemFont(ofSize: large ? 15 : 13, weight: large ? .semibold : .regular)
        return b
    }

    func buildUI() {
        let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 720, height: 660),
                           styleMask: [.titled, .closable, .miniaturizable],
                           backing: .buffered, defer: false)
        win.title = "CineForge AI"
        win.center()
        window = win

        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.edgeInsets = NSEdgeInsets(top: 22, left: 26, bottom: 18, right: 26)

        let icon = NSImageView()
        if let path = Bundle.main.path(forResource: "AppIcon", ofType: "icns"),
           let img = NSImage(contentsOfFile: path) {
            icon.image = img
        }
        icon.translatesAutoresizingMaskIntoConstraints = false
        icon.widthAnchor.constraint(equalToConstant: 76).isActive = true
        icon.heightAnchor.constraint(equalToConstant: 76).isActive = true

        let title = label("CineForge AI", size: 27, weight: .bold, center: true)
        let sub = label("Genera immagini e video con l'AI — il motore community è gratis, senza carta di credito.\nQuesta app avvia tutto sul tuo Mac, in locale.", size: 13,
                        color: .secondaryLabelColor, center: true)

        dockerLabel = label("Docker: controllo…")
        gitLabel = label("Git: controllo…")
        stateLabel = label("Pronto. Clicca il pulsante qui sotto per iniziare.", size: 14, weight: .medium)
        stateLabel.alignment = .center

        primaryButton = button("🚀  Prepara e avvia CineForge sul mio Mac", #selector(startClicked), large: true)
        openAppButton = button("🌐  Apri l'app nel browser", #selector(openAppClicked))
        stopButton = button("⛔  Ferma i servizi", #selector(stopClicked))
        let guideButton = button("📖  Guida passo-passo", #selector(guideClicked))
        let ghButton = button("⭐  Progetto su GitHub", #selector(githubClicked))

        let row1 = NSStackView(views: [openAppButton, stopButton])
        let row2 = NSStackView(views: [guideButton, ghButton])
        row1.spacing = 10
        row2.spacing = 10

        progress = NSProgressIndicator()
        progress.isIndeterminate = true
        progress.style = .spinning
        progress.controlSize = .small
        progress.translatesAutoresizingMaskIntoConstraints = false
        progress.widthAnchor.constraint(equalToConstant: 18).isActive = true
        progress.heightAnchor.constraint(equalToConstant: 18).isActive = true

        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.borderType = .bezelBorder
        scroll.translatesAutoresizingMaskIntoConstraints = false
        let tv = NSTextView()
        tv.isEditable = false
        tv.font = .monospacedSystemFont(ofSize: 11, weight: .regular)
        tv.textColor = .secondaryLabelColor
        tv.autoresizingMask = [.width]
        tv.isVerticallyResizable = true
        tv.frame = NSRect(x: 0, y: 0, width: 640, height: 120)
        scroll.documentView = tv
        scroll.heightAnchor.constraint(equalToConstant: 190).isActive = true
        scroll.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -18).isActive = true
        Log.view = tv

        let logTitle = label("Dettagli dell'avvio", size: 11, color: .tertiaryLabelColor)

        let spinnerRow = NSStackView(views: [progress, stateLabel])
        spinnerRow.spacing = 8
        spinnerRow.alignment = .centerY

        [icon, title, sub, dockerLabel, gitLabel, spinnerRow, primaryButton,
         row1, row2, logTitle, scroll].forEach { stack.addArrangedSubview($0) }

        let content = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: 720, height: 660))
        content.material = .underWindowBackground
        content.blendingMode = .behindWindow
        content.state = .active
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 0),
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -8),
        ])
        win.contentView = content
        win.makeKeyAndOrderFront(nil)
        makeMenu()
    }

    func makeMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "Esci da CineForge AI",
                                   action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appItem.submenu = appMenu
        NSApplication.shared.mainMenu = main
    }

    // MARK: State helpers (all UI mutations on main)

    func setState(_ text: String, spinner: Bool = false) {
        DispatchQueue.main.async {
            self.stateLabel.stringValue = text
            if spinner { self.progress.startAnimation(nil) } else { self.progress.stopAnimation(nil) }
        }
    }

    func setBusy(_ busy: Bool) {
        DispatchQueue.main.async {
            self.primaryButton.isEnabled = !busy
            self.stopButton.isEnabled = !busy
            if busy { self.progress.startAnimation(nil) } else { self.progress.stopAnimation(nil) }
        }
    }

    // MARK: Self checks

    func runSelfChecks() {
        queue.async {
            let dockerOk = Shell.quick("command -v docker >/dev/null && docker info >/dev/null 2>&1") == 0
            let gitOk = Shell.quick("command -v git >/dev/null") == 0
            DispatchQueue.main.async {
                self.dockerLabel.stringValue = dockerOk
                    ? "✅ Docker: installato e in esecuzione"
                    : (FileManager.default.fileExists(atPath: "/Applications/Docker.app")
                       ? "⚠️ Docker: installato ma non avviato (l'app lo avvierà per te)"
                       : "❌ Docker: non installato — serve Docker Desktop (gratuito). Premi Avvia e ti porto al download.")
                self.gitLabel.stringValue = gitOk ? "✅ Git: presente (di serie su macOS)" : "❌ Git: non trovato — installa gli Strumenti sviluppatore"
                self.primaryButton.isEnabled = gitOk  // docker may be bootstrapped by us
            }
            let up = Health.isUp()
            DispatchQueue.main.async { self.openAppButton.isEnabled = up }
            if up { Log.append("ℹ️ Servizi già attivi su localhost:3000 — puoi aprire l'app.") }
        }
    }

    // MARK: Actions

    @objc func startClicked() {
        setBusy(true)
        setState("Controllo Docker…", spinner: true)
        queue.async {
            if Shell.quick("command -v docker >/dev/null && docker info >/dev/null 2>&1") == 0 {
                Log.append("✅ Docker è pronto.")
                self.pickFolderAndInstall()
                return
            }
            if FileManager.default.fileExists(atPath: "/Applications/Docker.app") {
                Log.append("🐳 Docker non risponde: avvio Docker Desktop e attende la macchina…")
                DispatchQueue.main.async { NSWorkspace.shared.open(URL(fileURLWithPath: "/Applications/Docker.app")) }
                for _ in 0..<50 {  // up to ~150 s
                    if Shell.quick("docker info >/dev/null 2>&1") == 0 {
                        Log.append("✅ Docker è pronto.")
                        self.pickFolderAndInstall()
                        return
                    }
                    Thread.sleep(forTimeInterval: 3)
                }
                Log.append("❌ Docker non si è avviato in tempo.")
                self.setState("❌ Apri Docker Desktop manualmente (barra dei menu) e riprova.")
                self.setBusy(false)
                return
            }
            Log.append("❌ Docker Desktop non è installato. Apro la pagina di download (gratuito)…")
            DispatchQueue.main.async { NSWorkspace.shared.open(DOCKER_SITE) }
            self.setState("❌ Serve Docker Desktop: scaricalo, installalo, poi riprova.")
            self.setBusy(false)
        }
    }

    func pickFolderAndInstall() {
        guard let folder = PickFolder.ask() else {
            setState("Installazione annullata.")
            setBusy(false)
            return
        }
        let dir = folder.appendingPathComponent("cineforge", isDirectory: true)
        installDir = dir
        setState("Scarico il codice del progetto…", spinner: true)
        if FileManager.default.fileExists(atPath: dir.path) {
            Log.append("📂 Cartella «cineforge» già presente in \(dir.deletingLastPathComponent().path) — la riutilizzo (aggiornamento: esegui di nuovo «Ferma» + «Prepara e avvia»).")
            startCompose(dir: dir)
        } else {
            Shell.run("git clone --depth 1 \(REPO_URL) \"\(dir.path)\"") { code in
                if code != 0 {
                    self.setState("❌ Download fallito — controlla la connessione e riprova (dettagli sotto).")
                    self.setBusy(false)
                    return
                }
                Log.append("✅ Codice scaricato.")
                self.startCompose(dir: dir)
            }
        }
    }

    func startCompose(dir: URL) {
        setState("Costruisco e avvio i servizi (il primo avvio scarica molto: 5–15 minuti)…", spinner: true)
        Shell.run(COMPOSE_CMD + "up -d --build", cwd: dir) { code in
            if code != 0 {
                self.setState("❌ L'avvio è fallito — vedi i dettagli qui sotto (di solito è Docker fermo o memoria piena).")
                self.setBusy(false)
                return
            }
            Log.append("⏳ Servizi avviati: attendo che l'app risponda…")
            self.setState("⏳ Attendo che l'app risponda (le immagini si costruiscono: fino a ~15 minuti)…", spinner: true)
            for _ in 0..<200 {  // up to 20 min of polling
                if Health.isUp() {
                    Log.append("✅ Pronto! Apro il browser…")
                    self.setState("✅ Tutto avviato! Sto aprendo http://localhost:3000 nel browser.")
                    DispatchQueue.main.async {
                        NSWorkspace.shared.open(WEB_URL)
                        self.openAppButton.isEnabled = true
                    }
                    self.setBusy(false)
                    return
                }
                Thread.sleep(forTimeInterval: 6)
            }
            Log.append("⏱️ Non ancora risposto in 20 minuti: la costruzione può continuare in background.")
            self.setState("⏱️ Ancora in costruzione: riprova «Apri l'app nel browser» tra qualche minuto (i dettagli sotto mostrano i progressi).")
            self.setBusy(false)
        }
    }

    @objc func openAppClicked() {
        NSWorkspace.shared.open(WEB_URL)
    }

    @objc func stopClicked() {
        guard let dir = installDir, FileManager.default.fileExists(atPath: dir.path) else {
            Log.append("ℹ️ Nessuna installazione registrata: niente da fermare.")
            return
        }
        setState("Fermo i servizi…", spinner: true)
        Shell.run(COMPOSE_CMD + "down", cwd: dir) { _ in
            self.setState("⛔ Servizi fermati. Per riavviarli: «Prepara e avvia» (sarà rapido).")
            self.setBusy(false)
            DispatchQueue.main.async { self.openAppButton.isEnabled = false }
        }
    }

    @objc func guideClicked() {
        if let url = Bundle.main.url(forResource: "guida", withExtension: "html") {
            NSWorkspace.shared.open(url)
        } else {
            NSWorkspace.shared.open(REPO_LINK)
        }
    }

    @objc func githubClicked() {
        NSWorkspace.shared.open(REPO_LINK)
    }
}

// MARK: - App bootstrap

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
