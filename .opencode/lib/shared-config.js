// SHARED-CONFIG v1.0 — Single source of truth for project paths
// All plugins and lib modules should import ROOT from here instead of hardcoding.
// Derives ROOT from import.meta.url for portability across machines.
//
// USAGE:
//   import { ROOT, join } from "../lib/shared-config.js"
//   const logPath = join(ROOT, "data/sessions/my-log.log")

import { fileURLToPath } from "url"
import { dirname, resolve, join } from "path"

const __filename = fileURLToPath(import.meta.url)

// This file is at <root>/.opencode/lib/shared-config.js
// Project root is ../../ from here
export const ROOT = resolve(dirname(__filename), "../..")

// Re-export join for convenience so callers only need one import
export { join, resolve, dirname }
