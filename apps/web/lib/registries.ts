"use client";
import {create} from "zustand";
import {createJSONStorage, persist} from "zustand/middleware";

import type {CameraMove} from "./types";
import data from "../../../packages/shared/data/creative_registries.json";

export function group(id: string): Record<string, unknown>[] {
  return ((data as unknown as Record<string, Record<string, unknown>[]>)?.[id] ?? []);
}

export function names(id: string): {id: string; name: string}[] {
  return group(id).map((r) => ({id: r.id as string, name: r.name as string}));
}

export function cameraMoves(): CameraMove[] {
  return group("camera_moves") as unknown as CameraMove[];
}

export function palettes(): {id: string; name: string}[] {
  return names("palettes");
}
