/**
 CineForge AI launcher — native macOS app (AppKit + Network.framework, no dependencies, no storyboards).

 Two modes, chosen honestly:

 1. LIGHT MODE (default, needs nothing):
    The app opens a tiny built-in redirect server on http://localhost:3000 and opens the
    Light Studio in your browser (static page hosted for free, generation runs client-side
    on the AI Horde community engine). No Docker, no 6 GB of disk, no setup, no signup.
    Nothing but this ~2 MB launcher ever touches the disk.

 2. FULL LOCAL MODE (optional, advanced):
    The complete product on your Mac: clones the public repo and runs `docker compose up`
    (Postgres, Redis, API, web, worker). Needs Docker Desktop (free). Your database,
    your library, your own engine keys.

 Honesty rules (project principle): never fake success. If Docker is missing we say it;
 if compose fails we show the log; if the studio can't be reached we say so — we never
 pretend something is running when it isn't.
 */
import AppKit
import Network

let REPO_URL = "https://github.com/aertical17-byte/cineforge"
let REPO_LINK = URL(string: REPO_URL)!
let STUDIO_URL = URL(string: "https://cineforge-iota.vercel.app/studio/")!
let LOCAL_WEB_URL = URL(string: "http://127.0.0.1:3000/")!
let DOCKER_SITE = URL(string: "https://www.docker.com/products/docker-desktop/")!
let COMPOSE_CMD = "docker compose -f infra/docker/docker-compose.yml --project-directory . "

// MARK: - Built-in redirect server (light mode)

/// Serves exactly one thing on 127.0.0.1:3000: a 307 redirect to the hosted Light Studio.
/// This is what makes "the app opens localhost:3000 by itself" true with zero install weight.
final class RedirectServer {
    static let shared = RedirectServer()
    private var listener: NWListener?
    private(set) var running = false

    @discardableResult
    func start(port: UInt16 = 3000) -> Bool {
        stop()
        let params = NWParameters.tcp
        params.allowLocalEndpointReuse = true
        params.requiredLocalEndpoint = NWEndpoint.hostPort(host: "127.0.0.1", port: NWEndpoint.Port(rawValue: port)!)
        guard let l = try? NWListener(using: params) else { return false }
        l.newConnectionHandler = { conn in
            conn.start(queue: .global())
            conn.receive(minimumIncompleteLength: 1, maximumLength: 16384) { _, _, _, error in
                let location = STUDIO_URL.absoluteString
                let body = "CineForge AI Light Studio -> \(location)"
                let head = "HTTP/1.1 307 Temporary Redirect\r\n"
                    + "Location: \(location)\r\n"
                    + "Content-Type: text/plain; charset=utf-8\r\n"
                    + "Content-Length: \(body.utf8.count)\r\n"
                    + "Connection: close\r\n\r\n"
                let payload = (head + body).data(using: .utf8) ?? Data()
                conn.send(content: payload, completion: .contentProcessed { _ in conn.cancel() })
                if error != nil { conn.cancel() }
            }
        }
        l.stateUpdateHandler = { [weak self] state in
            Dlog("[launcher] listener state: \(state)")
            if case .ready = state { self?.running = true }
            if case .failed = state { self?.running = false }
        }
        listener = l
        l.start(queue: .global())
        return true
    }

    func stop() {
        listener?.cancel()
        listener = nil
        running = false
    }
}

// MARK: - Small helpers

/// Console log for debugging when the binary runs from a terminal (visible in stderr).
/// Raw write(2): immune to FileHandle/Foundation buffering or descriptor weirdness.
func Dlog(_ s: String) {
    let bytes = Array((s + "\n").utf8)
    bytes.withUnsafeBufferPointer { buf in
        var sent = 0
        while sent < buf.count {
            let n = write(2, buf.baseAddress! + sent, buf.count - sent)
            if n <= 0 { break }
            sent += n
        }
    }
}

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
    static func isUp(_ url: URL = LOCAL_WEB_URL, timeout: TimeInterval = 3) -> Bool {
        let box = Box()
        var req = URLRequest(url: url)
        req.timeoutInterval = timeout
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
            panel.prompt = "Choose Folder"
            panel.message = "Where should the full local mode live? A “cineforge” subfolder will be created."
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
    var lightLabel: NSTextField!
    var dockerLabel: NSTextField!
    var stateLabel: NSTextField!
    var openStudioButton: NSButton!
    var fullModeButton: NSButton!
    var dockerSection: NSView!
    var primaryButton: NSButton!
    var openAppButton: NSButton!
    var stopButton: NSButton!
    var progress: NSProgressIndicator!
    var autoOpen: NSButton!
    var fullModeVisible = false
    var installDir: URL? {
        get { UserDefaults.standard.url(forKey: "installDir") }
        set { UserDefaults.standard.set(newValue, forKey: "installDir") }
    }
    let queue = DispatchQueue(label: "cineforge.launcher", qos: .userInitiated)

    func applicationDidFinishLaunching(_ note: Notification) {
        Dlog("[launcher] applicationDidFinishLaunching: enter")
        AppDelegate.shared = self
        buildUI()
        Dlog("[launcher] buildUI returned")
        startLightMode()   // first: the default path must never wait behind slow probes
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

    func button(_ title: String, _ sel: Selector, large: Bool = false, bezel: NSButton.BezelStyle = .rounded) -> NSButton {
        let b = NSButton(title: title, target: self, action: sel)
        b.bezelStyle = bezel
        b.controlSize = large ? .large : .regular
        b.font = .systemFont(ofSize: large ? 15 : 13, weight: large ? .semibold : .regular)
        return b
    }

    func buildUI() {
        Dlog("[launcher] buildUI: enter")
        let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 720, height: 700),
                           styleMask: [.titled, .closable, .miniaturizable],
                           backing: .buffered, defer: false)
        win.title = "CineForge AI"
        win.center()
        window = win

        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 11
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.edgeInsets = NSEdgeInsets(top: 20, left: 26, bottom: 16, right: 26)

        let icon = NSImageView()
        if let path = Bundle.main.path(forResource: "AppIcon", ofType: "icns"),
           let img = NSImage(contentsOfFile: path) {
            icon.image = img
        }
        icon.translatesAutoresizingMaskIntoConstraints = false
        icon.widthAnchor.constraint(equalToConstant: 72).isActive = true
        icon.heightAnchor.constraint(equalToConstant: 72).isActive = true

        let title = label("CineForge AI", size: 26, weight: .bold, center: true)
        let sub = label("Light mode: the studio opens in your browser — no Docker, no setup, nothing installs on your Mac.\nThe community engine generates images for free. Full local mode stays available below (optional).",
                        size: 12.5, color: .secondaryLabelColor, center: true)

        lightLabel = label("🌐 Light Studio: preparing…", size: 13.5, weight: .medium)
        dockerLabel = label("🐳 Full local mode (optional): Docker unchecked", size: 12, color: .secondaryLabelColor)

        autoOpen = NSButton(title: "Open the Studio automatically when the app starts",
                            target: self, action: #selector(autoOpenToggled))
        autoOpen.setButtonType(.switch)
        autoOpen.state = UserDefaults.standard.object(forKey: "autoOpen") == nil || UserDefaults.standard.bool(forKey: "autoOpen") ? .on : .off

        openStudioButton = button("🌐  Open the Studio", #selector(openStudioClicked), large: true, bezel: .rounded)
        openStudioButton.controlSize = .large

        fullModeButton = button("🐳  Full local mode (Docker) — show options", #selector(toggleFullMode), large: false)

        // advanced docker section (hidden until toggled)
        primaryButton = button("🚀  Set up the full local mode (Docker)", #selector(startClicked), large: true)
        openAppButton = button("🖥  Open localhost:3000 (local app)", #selector(openAppClicked))
        stopButton = button("⛔  Stop services", #selector(stopClicked))
        let dockerRow = NSStackView(views: [openAppButton, stopButton])
        dockerRow.spacing = 10
        primaryButton.controlSize = .large

        dockerSection = NSStackView(views: [primaryButton, dockerRow])
        (dockerSection as! NSStackView).orientation = .vertical
        (dockerSection as! NSStackView).alignment = .centerX
        (dockerSection as! NSStackView).spacing = 10
        dockerSection.isHidden = true

        let guideButton = button("📖  Guide", #selector(guideClicked))
        let ghButton = button("⭐  Project on GitHub", #selector(githubClicked))
        let row2 = NSStackView(views: [guideButton, ghButton])
        row2.spacing = 10

        progress = NSProgressIndicator()
        progress.isIndeterminate = true
        progress.style = .spinning
        progress.controlSize = .small
        progress.translatesAutoresizingMaskIntoConstraints = false
        progress.widthAnchor.constraint(equalToConstant: 18).isActive = true
        progress.heightAnchor.constraint(equalToConstant: 18).isActive = true

        stateLabel = label("Light Studio is starting…", size: 13.5, weight: .medium)

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
        tv.frame = NSRect(x: 0, y: 0, width: 640, height: 110)
        scroll.documentView = tv
        scroll.heightAnchor.constraint(equalToConstant: 150).isActive = true
        Log.view = tv

        let logTitle = label("Details", size: 11, color: .tertiaryLabelColor)

        let spinnerRow = NSStackView(views: [progress, stateLabel])
        spinnerRow.spacing = 8
        spinnerRow.alignment = .centerY

        [icon, title, sub, lightLabel, autoOpen, openStudioButton, fullModeButton,
         dockerSection, dockerLabel, spinnerRow, row2, logTitle, scroll].forEach { stack.addArrangedSubview($0) }

        let content = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: 720, height: 700))
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
        // scroll width: safe to activate NOW — scroll (inside stack) lives in the window hierarchy
        scroll.widthAnchor.constraint(equalTo: content.widthAnchor, constant: -52).isActive = true

        // Robust visibility: the launcher must ALWAYS show its window, whatever launched it.
        win.makeKeyAndOrderFront(nil)
        win.orderFrontRegardless()
        NSApp.activate(ignoringOtherApps: true)
        makeMenu()
    }

    func makeMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        main.addItem(appItem)
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "Quit CineForge AI",
                                   action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appItem.submenu = appMenu
        NSApplication.shared.mainMenu = main
    }

    // MARK: Light mode

    func startLightMode() {
        DispatchQueue.global(qos: .userInitiated).async {
            Dlog("[launcher] startLightMode: begin")
            let alreadyLocal = Health.isUp(timeout: 1.5)  // full local mode already serving?
            Dlog("[launcher] alreadyLocal=\(alreadyLocal)")
            if alreadyLocal {
                DispatchQueue.main.async {
                    self.lightLabel.stringValue = "🌐 Full local mode detected on localhost:3000 — using it."
                    self.stateLabel.stringValue = "✅ The local app is running. Opening it…"
                    self.openAppButton.isEnabled = true
                }
                NSWorkspace.shared.open(LOCAL_WEB_URL)
                Log.append("ℹ️ Something already serves localhost:3000 (full local mode). Not starting the redirect server.")
                return
            }
            let started = RedirectServer.shared.start()
            Dlog("[launcher] RedirectServer.start() -> \(started)")
            DispatchQueue.main.async {
                if started {
                    self.lightLabel.stringValue = "🌐 Light Studio: ready at http://localhost:3000 → opens in your browser"
                    self.stateLabel.stringValue = "✅ Ready. Nothing to install, no Docker, no signup."
                    self.openStudioButton.isEnabled = true
                    Log.append("✅ Redirect server live on 127.0.0.1:3000 → \(STUDIO_URL.absoluteString)")
                    if self.autoOpen.state == .on { NSWorkspace.shared.open(LOCAL_WEB_URL) }
                } else {
                    self.lightLabel.stringValue = "🌐 Light Studio: port 3000 busy — opening the studio URL directly."
                    self.openStudioButton.isEnabled = true
                    Log.append("⚠️ Could not bind port 3000 (something else is using it). Opening the studio URL directly.")
                    if self.autoOpen.state == .on { NSWorkspace.shared.open(STUDIO_URL) }
                }
            }
        }
    }

    @objc func autoOpenToggled() {
        UserDefaults.standard.set(autoOpen.state == .on, forKey: "autoOpen")
    }

    @objc func openStudioClicked() {
        NSWorkspace.shared.open(STUDIO_URL)
    }

    // MARK: Full local mode (optional)

    @objc func toggleFullMode() {
        fullModeVisible.toggle()
        fullModeButton.title = fullModeVisible
            ? "🐳  Full local mode (Docker) — hide options"
            : "🐳  Full local mode (Docker) — show options"
        window.setContentSize(NSSize(width: 720, height: fullModeVisible ? 860 : 700))
        dockerSection.isHidden = !fullModeVisible
        dockerLabel.isHidden = !fullModeVisible
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
                    ? "🐳 Docker: installed and running (full local mode available)"
                    : (FileManager.default.fileExists(atPath: "/Applications/Docker.app")
                       ? "🐳 Docker: installed but not running — needed only for the optional full local mode"
                       : "🐳 Docker: not installed — NOT needed for the Light Studio; only for the optional full local mode")
                self.fullModeButton.isEnabled = gitOk
            }
            let studioUp = Health.isUp(STUDIO_URL, timeout: 4)
            DispatchQueue.main.async {
                if studioUp {
                    Log.append("✅ Light Studio reachable online.")
                } else {
                    Log.append("⚠️ Light Studio not reachable right now (offline?). Generation needs internet.")
                    self.lightLabel.stringValue = "🌐 Light Studio: offline — check your connection."
                }
            }
            let up = Health.isUp()
            DispatchQueue.main.async { self.openAppButton.isEnabled = up }
            if up { Log.append("ℹ️ Services already running on localhost:3000 — you can open the local app.") }
        }
    }

    // MARK: Actions (full local mode)

    @objc func startClicked() {
        setBusy(true)
        setState("Checking Docker…", spinner: true)
        queue.async {
            if Shell.quick("command -v docker >/dev/null && docker info >/dev/null 2>&1") == 0 {
                Log.append("✅ Docker is ready.")
                self.pickFolderAndInstall()
                return
            }
            if FileManager.default.fileExists(atPath: "/Applications/Docker.app") {
                Log.append("🐳 Docker not responding: starting Docker Desktop and waiting for the engine…")
                DispatchQueue.main.async { NSWorkspace.shared.open(URL(fileURLWithPath: "/Applications/Docker.app")) }
                for _ in 0..<50 {  // up to ~150 s
                    if Shell.quick("docker info >/dev/null 2>&1") == 0 {
                        Log.append("✅ Docker is ready.")
                        self.pickFolderAndInstall()
                        return
                    }
                    Thread.sleep(forTimeInterval: 3)
                }
                Log.append("❌ Docker didn't start in time.")
                self.setState("❌ Open Docker Desktop manually (menu bar) and try again.")
                self.setBusy(false)
                return
            }
            Log.append("❌ Docker Desktop is not installed. Opening the download page (free)…")
            DispatchQueue.main.async { NSWorkspace.shared.open(DOCKER_SITE) }
            self.setState("❌ Full local mode needs Docker Desktop: download it, install it, then try again. (The Light Studio never needs it.)")
            self.setBusy(false)
        }
    }

    func pickFolderAndInstall() {
        guard let folder = PickFolder.ask() else {
            setState("Installation canceled.")
            setBusy(false)
            return
        }
        let dir = folder.appendingPathComponent("cineforge", isDirectory: true)
        installDir = dir
        setState("Downloading the project code…", spinner: true)
        if FileManager.default.fileExists(atPath: dir.path) {
            Log.append("📂 A “cineforge” folder already exists in \(dir.deletingLastPathComponent().path) — reusing it (to update: run “Stop” + “Set up” again).")
            startCompose(dir: dir)
        } else {
            Shell.run("git clone --depth 1 \(REPO_URL) \"\(dir.path)\"") { code in
                if code != 0 {
                    self.setState("❌ Download failed — check your connection and try again (details below).")
                    self.setBusy(false)
                    return
                }
                Log.append("✅ Code downloaded.")
                self.startCompose(dir: dir)
            }
        }
    }

    func startCompose(dir: URL) {
        setState("Building & starting services (the first run downloads a lot: 5–15 minutes)…", spinner: true)
        Shell.run(COMPOSE_CMD + "up -d --build", cwd: dir) { code in
            if code != 0 {
                self.setState("❌ Startup failed — see the details below (usually Docker stopped or low memory).")
                self.setBusy(false)
                return
            }
            Log.append("⏳ Services started: waiting for the app to respond…")
            self.setState("⏳ Waiting for the app to respond (images are being built: up to ~15 minutes)…", spinner: true)
            for _ in 0..<200 {  // up to 20 min of polling
                if Health.isUp() {
                    Log.append("✅ Ready! Opening the browser…")
                    self.setState("✅ Full local mode is up! Opening http://localhost:3000 in your browser.")
                    DispatchQueue.main.async {
                        self.lightLabel.stringValue = "🌐 Full local mode serving localhost:3000."
                        NSWorkspace.shared.open(LOCAL_WEB_URL)
                        self.openAppButton.isEnabled = true
                    }
                    self.setBusy(false)
                    return
                }
                Thread.sleep(forTimeInterval: 6)
            }
            Log.append("⏱️ Still no response after 20 minutes: the build may continue in the background.")
            self.setState("⏱️ Still building: try “Open localhost:3000” again in a few minutes (details below show progress).")
            self.setBusy(false)
        }
    }

    @objc func openAppClicked() {
        NSWorkspace.shared.open(LOCAL_WEB_URL)
    }

    @objc func stopClicked() {
        guard let dir = installDir, FileManager.default.fileExists(atPath: dir.path) else {
            Log.append("ℹ️ No installation registered: nothing to stop.")
            return
        }
        setState("Stopping services…", spinner: true)
        Shell.run(COMPOSE_CMD + "down", cwd: dir) { _ in
            self.setState("⛔ Services stopped. To restart: “Set up the full local mode” again (it will be quick).")
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

Dlog("[launcher] bootstrap: enter")
let app = NSApplication.shared
Dlog("[launcher] bootstrap: NSApplication.shared ok")
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
Dlog("[launcher] bootstrap: calling app.run()")
app.run()
