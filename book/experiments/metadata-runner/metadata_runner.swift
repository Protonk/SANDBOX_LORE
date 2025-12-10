import Foundation
import Darwin

@_silgen_name("lutimes")
func lutimes(_ file: UnsafePointer<CChar>!, _ times: UnsafePointer<timeval>!) -> Int32

@_silgen_name("sandbox_init")
func sandbox_init(_ profile: UnsafePointer<CChar>, _ flags: UInt64, _ errorbuf: UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>!) -> Int32

@_silgen_name("sandbox_free_error")
func sandbox_free_error(_ errorbuf: UnsafeMutablePointer<CChar>!)

// Minimal struct matching libsandbox sandbox_profile_t
struct SandboxProfile {
    var builtin: UnsafeMutablePointer<CChar>?
    var data: UnsafePointer<UInt8>?
    var size: Int
}

typealias SandboxApplyFn = @convention(c) (UnsafeMutableRawPointer?) -> Int32

struct RunResult: Codable {
    let op: String
    let path: String
    let syscall: String
    let attr_payload: String?
    let status: String
    let errno: Int32?
    let errno_name: String?
    let message: String?
    let apply_rc: Int32
    let apply_errno: Int32?
    let apply_errno_name: String?
    let apply_mode: String
    let apply_message: String?
}

func errnoName(_ code: Int32) -> String {
    switch code {
    case 0: return "OK"
    case EPERM: return "EPERM"
    case EACCES: return "EACCES"
    case ENOENT: return "ENOENT"
    case ENOTDIR: return "ENOTDIR"
    case ENOSPC: return "ENOSPC"
    case EROFS: return "EROFS"
    case EINVAL: return "EINVAL"
    case ENOTSUP: return "ENOTSUP"
    case EIO: return "EIO"
    default: return "errno_\(code)"
    }
}

func usage() -> Never {
    fputs("Usage: metadata_runner (--sbpl <profile.sb> | --blob <profile.sb.bin>) --op <file-read-metadata|file-write*> --path <target> [--syscall <lstat|getattrlist|setattrlist|chmod|utimes>] [--attr-payload <cmn|cmn-name|cmn-times|file-size>] [--chmod-mode <octal>]\n", stderr)
    exit(64) // EX_USAGE
}

func applySandbox(blobPath: String?, sbplPath: String?) -> (rc: Int32, err: Int32?, message: String?, mode: String) {
    if let sbplPath {
        errno = 0
        guard let sbpl = try? String(contentsOfFile: sbplPath, encoding: .utf8) else {
            return (rc: -2, err: errno, message: "failed to read sbpl", mode: "sbpl")
        }
        var errBuf: UnsafeMutablePointer<CChar>? = nil
        let rc = sbpl.withCString { cstr in
            sandbox_init(cstr, 0, &errBuf)
        }
        let message = errBuf.map { String(cString: $0) }
        if let errBuf {
            sandbox_free_error(errBuf)
        }
        let applyErr = errno == 0 ? nil : errno
        return (rc: rc, err: applyErr, message: message, mode: "sbpl")
    }

    guard let blobPath else {
        return (rc: -3, err: nil, message: "no profile path provided", mode: "none")
    }

    guard let handle = dlopen("/usr/lib/libsandbox.1.dylib", RTLD_NOW | RTLD_LOCAL) else {
        return (rc: -1, err: errno, message: "dlopen libsandbox failed", mode: "blob")
    }
    defer { dlclose(handle) }

    guard let symbol = dlsym(handle, "sandbox_apply") else {
        return (rc: -1, err: errno, message: "dlsym sandbox_apply failed", mode: "blob")
    }
    let apply = unsafeBitCast(symbol, to: SandboxApplyFn.self)

    do {
        let data = try Data(contentsOf: URL(fileURLWithPath: blobPath))
        let rc: Int32 = data.withUnsafeBytes { buf -> Int32 in
            var profile = SandboxProfile(builtin: nil, data: buf.bindMemory(to: UInt8.self).baseAddress, size: data.count)
            return withUnsafeMutablePointer(to: &profile) { ptr -> Int32 in
                errno = 0
                return apply(UnsafeMutableRawPointer(ptr))
            }
        }
        let applyErrno = rc == 0 ? nil : errno
        return (rc: rc, err: applyErrno, message: nil, mode: "blob")
    } catch {
        return (rc: -2, err: errno, message: "failed to load blob", mode: "blob")
    }
}

struct AttrPayload {
    let attrlist: attrlist
    let buffer: [UInt8]
}

func makeAttrPayload(kind: String) -> AttrPayload {
    var attr = attrlist()
    attr.bitmapcount = UInt16(ATTR_BIT_MAP_COUNT)
    var buf = [UInt8]()
    switch kind {
    case "cmn-name":
        attr.commonattr = UInt32(ATTR_CMN_NAME)
        buf = Array(repeating: 0, count: 256)
    case "cmn-times":
        attr.commonattr = UInt32(ATTR_CMN_MODTIME | ATTR_CMN_CHGTIME)
        var timespecs = [
            timespec(tv_sec: time_t(time(nil)), tv_nsec: 0),
            timespec(tv_sec: time_t(time(nil)), tv_nsec: 0),
        ]
        buf = withUnsafeBytes(of: &timespecs) { Array($0) }
    case "file-size":
        attr.fileattr = UInt32(ATTR_FILE_TOTALSIZE)
        var size: UInt64 = 0
        buf = withUnsafeBytes(of: &size) { Array($0) }
    case "cmn":
        fallthrough
    default:
        attr.commonattr = UInt32(ATTR_CMN_NAME)
        buf = Array(repeating: 0, count: 256)
    }
    return AttrPayload(attrlist: attr, buffer: buf)
}

func performOperation(op: String, syscall: String, path: String, chmodMode: mode_t, attrPayload: AttrPayload?) -> (status: String, err: Int32?, message: String?) {
    var opErrno: Int32 = 0
    let cPath = path.cString(using: .utf8)!

    func openFd(_ flags: Int32 = O_RDONLY) -> Int32 {
        errno = 0
        let fd = open(cPath, flags)
        if fd == -1 {
            opErrno = errno
        }
        return fd
    }

    switch (op, syscall) {
    case ("file-read-metadata", "lstat"):
        var st = stat()
        errno = 0
        let rv = lstat(cPath, &st)
        if rv == 0 {
            return ("ok", 0, "stat-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-read-metadata", "getattrlist"):
        let payload = attrPayload ?? makeAttrPayload(kind: "cmn")
        var attr = payload.attrlist
        var buf = payload.buffer
        errno = 0
        let rv = buf.withUnsafeMutableBytes { bytes -> Int32 in
            return getattrlist(cPath, &attr, bytes.baseAddress, bytes.count, 0)
        }
        if rv == 0 {
            return ("ok", 0, "getattrlist-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-read-metadata", "setattrlist"):
        let payload = attrPayload ?? makeAttrPayload(kind: "cmn")
        var attr = payload.attrlist
        var buf = payload.buffer
        errno = 0
        let rv = buf.withUnsafeMutableBytes { bytes -> Int32 in
            return setattrlist(cPath, &attr, bytes.baseAddress, bytes.count, 0)
        }
        if rv == 0 {
            return ("ok", 0, "setattrlist-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-read-metadata", "fstat"):
        let fd = openFd()
        if fd == -1 {
            return ("op_failed", opErrno, "open failed")
        }
        var st = stat()
        errno = 0
        let rv = fstat(fd, &st)
        let savedErr = errno
        close(fd)
        if rv == 0 {
            return ("ok", 0, "fstat-ok")
        } else {
            opErrno = savedErr
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "chmod"):
        errno = 0
        let rv = chmod(cPath, chmodMode)
        if rv == 0 {
            return ("ok", 0, "chmod-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "utimes"):
        var now = time_t(time(nil))
        var times = [
            timeval(tv_sec: now, tv_usec: 0),
            timeval(tv_sec: now, tv_usec: 0),
        ]
        errno = 0
        let rv = times.withUnsafeBufferPointer { ptr -> Int32 in
            return utimes(cPath, ptr.baseAddress)
        }
        if rv == 0 {
            return ("ok", 0, "utimes-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "fchmod"):
        let fd = openFd(O_WRONLY)
        if fd == -1 {
            return ("op_failed", opErrno, "open failed")
        }
        errno = 0
        let rv = fchmod(fd, chmodMode)
        let savedErr = errno
        close(fd)
        if rv == 0 {
            return ("ok", 0, "fchmod-ok")
        } else {
            opErrno = savedErr
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "futimes"):
        let fd = openFd(O_WRONLY)
        if fd == -1 {
            return ("op_failed", opErrno, "open failed")
        }
        let now = time_t(time(nil))
        let times = [
            timeval(tv_sec: now, tv_usec: 0),
            timeval(tv_sec: now, tv_usec: 0),
        ]
        errno = 0
        let rv = times.withUnsafeBufferPointer { ptr -> Int32 in
            return futimes(fd, ptr.baseAddress)
        }
        let savedErr = errno
        close(fd)
        if rv == 0 {
            return ("ok", 0, "futimes-ok")
        } else {
            opErrno = savedErr
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "lchown"):
        let uid = getuid()
        let gid = getgid()
        errno = 0
        let rv = lchown(cPath, uid, gid)
        if rv == 0 {
            return ("ok", 0, "lchown-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "fchown"):
        let fd = openFd(O_WRONLY)
        if fd == -1 {
            return ("op_failed", opErrno, "open failed")
        }
        let uid = getuid()
        let gid = getgid()
        errno = 0
        let rv = fchown(fd, uid, gid)
        let savedErr = errno
        close(fd)
        if rv == 0 {
            return ("ok", 0, "fchown-ok")
        } else {
            opErrno = savedErr
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "fchownat"):
        let uid = getuid()
        let gid = getgid()
        errno = 0
        let rv = fchownat(AT_FDCWD, cPath, uid, gid, 0)
        if rv == 0 {
            return ("ok", 0, "fchownat-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    case ("file-write*", "lutimes"):
        let now = time_t(time(nil))
        let times = [
            timeval(tv_sec: now, tv_usec: 0),
            timeval(tv_sec: now, tv_usec: 0),
        ]
        errno = 0
        let rv = times.withUnsafeBufferPointer { ptr -> Int32 in
            return lutimes(cPath, ptr.baseAddress)
        }
        if rv == 0 {
            return ("ok", 0, "lutimes-ok")
        } else {
            opErrno = errno
            return ("op_failed", opErrno, String(cString: strerror(opErrno)))
        }
    default:
        return ("invalid_op", nil, "unsupported \(op) syscall \(syscall)")
    }
}

func main() {
    let args = CommandLine.arguments
    var blobPath: String?
    var sbplPath: String?
    var op: String?
    var targetPath: String?
    var chmodMode: mode_t = 0o640
    var syscallName: String?
    var attrPayloadKind: String?

    var idx = 1
    while idx < args.count {
        let arg = args[idx]
        switch arg {
        case "--blob":
            guard idx + 1 < args.count else { usage() }
            blobPath = args[idx + 1]
            idx += 2
        case "--op":
            guard idx + 1 < args.count else { usage() }
            op = args[idx + 1]
            idx += 2
        case "--sbpl":
            guard idx + 1 < args.count else { usage() }
            sbplPath = args[idx + 1]
            idx += 2
        case "--path":
            guard idx + 1 < args.count else { usage() }
            targetPath = args[idx + 1]
            idx += 2
        case "--chmod-mode":
            guard idx + 1 < args.count else { usage() }
            let value = args[idx + 1]
            if let parsed = Int(value, radix: 8) {
                chmodMode = mode_t(parsed)
            }
            idx += 2
        case "--syscall":
            guard idx + 1 < args.count else { usage() }
            syscallName = args[idx + 1]
            idx += 2
        case "--attr-payload":
            guard idx + 1 < args.count else { usage() }
            attrPayloadKind = args[idx + 1]
            idx += 2
        default:
            usage()
        }
    }

    guard (blobPath != nil || sbplPath != nil), let op, let targetPath else {
        usage()
    }
    if op != "file-read-metadata" && op != "file-write*" {
        usage()
    }
    if syscallName == nil {
        syscallName = (op == "file-read-metadata") ? "lstat" : "chmod"
    }
    let attrPayload = makeAttrPayload(kind: attrPayloadKind ?? "cmn")

    let applyResult = applySandbox(blobPath: blobPath, sbplPath: sbplPath)
    if applyResult.rc != 0 {
        let result = RunResult(
            op: op,
            path: targetPath,
            syscall: syscallName ?? "unknown",
            attr_payload: attrPayloadKind,
            status: "apply_failed",
            errno: nil,
            errno_name: nil,
            message: "sandbox apply rc \(applyResult.rc)",
            apply_rc: applyResult.rc,
            apply_errno: applyResult.err,
            apply_errno_name: applyResult.err.map { errnoName($0) },
            apply_mode: applyResult.mode,
            apply_message: applyResult.message
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        if let data = try? encoder.encode(result) {
            FileHandle.standardOutput.write(data)
            FileHandle.standardOutput.write("\n".data(using: .utf8)!)
        }
        exit(0)
    }

    let opResult = performOperation(op: op, syscall: syscallName ?? "unknown", path: targetPath, chmodMode: chmodMode, attrPayload: attrPayload)
    let final = RunResult(
        op: op,
        path: targetPath,
        syscall: syscallName ?? "unknown",
        attr_payload: attrPayloadKind,
        status: opResult.status,
        errno: opResult.err,
        errno_name: opResult.err.map { errnoName($0) },
        message: opResult.message,
        apply_rc: applyResult.rc,
        apply_errno: applyResult.err,
        apply_errno_name: applyResult.err.map { errnoName($0) },
        apply_mode: applyResult.mode,
        apply_message: applyResult.message
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    if let data = try? encoder.encode(final) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write("\n".data(using: .utf8)!)
    }
}

main()
