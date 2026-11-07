/** Renders the design-system primitives without a Next runtime. */
import {render} from "@testing-library/react";
import {describe, expect, it} from "vitest";

import {Badge, Button, Card, EmptyState, Tabs} from "@/components/ui";

describe("design-system primitives", () => {
  it("renders Button with variant styling", () => {
    const {container} = render(<Button variant="primary">Generate</Button>);
    expect(container.querySelector("button")?.className).toContain("bg-byz-500");
  });
  it("renders Badge tones", () => {
    const {getByText} = render(<Badge tone="accent">ready</Badge>);
    expect(getByText("ready").className).toContain("byz-300");
  });
  it("renders Tabs and switches active programmatically", () => {
    const {getByRole} = render(<Tabs items={[{id: "a", label: "A"}, {id: "b", label: "B"}]} active="b" onChange={() =>undefined} />);
    expect(getByRole("tab", {name: "B"}).getAttribute("aria-selected")).toBe("true");
  });
  it("renders EmptyState body copy", () => {
    const {getByText} = render(<EmptyState title="Nothing yet" body="Run a generation." />);
    expect(getByText("Run a generation.")).toBeTruthy();
  });
  it("Card is styled container", () => {
    const {container} = render(<Card><p>inner</p></Card>);
    expect(container.firstElementChild?.className).toContain("bg-ink-850");
  });
});
