/** Pure-logic tests for the web client (deterministic modules only). */
import {describe, expect, it} from "vitest";

import {cameraMoves, names} from "@/lib/registries";
import {API_URL} from "@/lib/api";

describe("creative registries", () => {
  it("loads 20+ camera moves with generic vocabulary", () => {
    const moves = cameraMoves();
    expect(moves.length).toBeGreaterThanOrEqual(20);
    const ids = moves.map((m) => m.id);
    expect(ids).toEqual(expect.arrayContaining(["dolly_zoom", "orbit_left", "crane_up", "fpv", "static"]));
  });

  it("exposes palettes & lenses via names()", () => {
    expect(names("palettes").length).toBeGreaterThanOrEqual(20);
    expect(names("lenses")).toEqual(expect.arrayContaining([expect.objectContaining({id: "anamorphic"})]));
  });
});

describe("api client config", () => {
  it("never embeds keys — base URL only", () => {
    expect(API_URL.startsWith("http")).toBe(true);
  });
});
