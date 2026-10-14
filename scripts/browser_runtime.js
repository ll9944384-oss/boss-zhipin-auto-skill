"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

function existing(paths) {
  return paths.find((candidate) => candidate && fs.existsSync(candidate)) || "";
}

function browserCandidates(preferred = "", platform = process.platform, env = process.env) {
  const home = os.homedir();
  const local = env.LOCALAPPDATA || "";
  const programFiles = env.PROGRAMFILES || "C:\\Program Files";
  const programFilesX86 = env["PROGRAMFILES(X86)"] || "C:\\Program Files (x86)";
  const edge = platform === "win32" ? [
    path.join(programFilesX86, "Microsoft", "Edge", "Application", "msedge.exe"),
    path.join(programFiles, "Microsoft", "Edge", "Application", "msedge.exe"),
    local && path.join(local, "Microsoft", "Edge", "Application", "msedge.exe"),
  ] : [];
  const chrome = platform === "win32" ? [
    path.join(programFiles, "Google", "Chrome", "Application", "chrome.exe"),
    path.join(programFilesX86, "Google", "Chrome", "Application", "chrome.exe"),
    local && path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
  ] : platform === "darwin" ? [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    path.join(home, "Applications", "Google Chrome.app", "Contents", "MacOS", "Google Chrome"),
  ] : [
    "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  ];
  const pref = String(preferred || env.HERMES_BROWSER || "").toLowerCase();
  return pref.includes("chrome") ? [...chrome, ...edge] : [...edge, ...chrome];
}

function resolveBrowserExecutable(preferred = "") {
  const executable = existing(browserCandidates(preferred));
  if (!executable) {
    throw new Error(`No supported Edge/Chrome executable found on ${process.platform}. Install Microsoft Edge or Google Chrome, or set HERMES_BROWSER.`);
  }
  return executable;
}

function browserName(executable) {
  return /msedge/i.test(executable) ? "Microsoft Edge" : /chrome/i.test(executable) ? "Google Chrome" : "Chromium";
}

module.exports = { browserCandidates, resolveBrowserExecutable, browserName };
