import Foundation
import Darwin

typealias ExtractFn = @convention(c) (
  UnsafePointer<CChar>?,
  UnsafePointer<CChar>?,
  (@convention(block) (UInt32, UInt32) -> Void)?
) -> Int32

let args = CommandLine.arguments
if args.count != 3 {
  fputs("usage: extract_dsc <path-to-dyld_shared_cache> <output-dir>\n", stderr)
  exit(2)
}

let candidates = [
  "/usr/lib/dsc_extractor.bundle",
  "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/usr/lib/dsc_extractor.bundle",
]

guard let bundlePath = candidates.first(where: { FileManager.default.fileExists(atPath: $0) }) else {
  fputs("dsc_extractor.bundle not found. Install Xcode if needed.\n", stderr)
  exit(1)
}

guard let handle = dlopen(bundlePath, RTLD_NOW) else {
  fputs("dlopen failed\n", stderr)
  exit(1)
}

defer { dlclose(handle) }

guard let sym = dlsym(handle, "dyld_shared_cache_extract_dylibs_progress") else {
  fputs("symbol not found in bundle\n", stderr)
  exit(1)
}

guard let fn = unsafeBitCast(sym, to: Optional<ExtractFn>.self) else {
  fputs("could not cast symbol\n", stderr)
  exit(1)
}

let rc = fn(args[1], args[2]) { cur, total in
  if total > 0 {
    fputs("\rExtracting \(cur)/\(total)", stderr)
  }
}
fputs("\n", stderr)
if rc != 0 {
  fputs("extraction failed rc=\(rc)\n", stderr)
  exit(rc)
}
