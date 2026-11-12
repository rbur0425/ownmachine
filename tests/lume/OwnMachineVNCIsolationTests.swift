import Foundation
import Testing
@testable import lume

@MainActor
private final class OwnMachineMacVM: MockVM {
    override func getOSType() -> String { "macOS" }
}
private enum OwnMachineProbe: Error { case captured }

@MainActor
@Test("macOS normal and USB boot never add an implicit VNC credential share")
func ownMachineVNCCredentialIsolation() async throws {
    for usb in [false, true] {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let directory = VMDirectory(Path(root.path))
        try Data(repeating: 0, count: 1024).write(to: directory.diskPath.url)
        try Data(repeating: 0, count: 1024).write(to: directory.nvramPath.url)
        var config = try VMConfig(os: "macOS", cpuCount: 1, memorySize: 1024,
                                  diskSize: 1024, display: "1024x768")
        config.setMacAddress("00:11:22:33:44:55")
        try directory.saveConfig(config)
        try Data().write(to: directory.dir.file(".initialized").url)
        let context = VMDirContext(dir: directory, config: config,
                                   home: Home(fileManager: .default), storage: nil)
        var captured = false
        let vm = OwnMachineMacVM(vmDirContext: context, virtualizationServiceFactory: { candidate in
            captured = true
            #expect(candidate.sharedDirectories?.isEmpty != false)
            throw OwnMachineProbe.captured
        }, vncServiceFactory: { MockVNCService(vmDirectory: $0) })
        do {
            if usb {
                try await vm.runWithUSBStorage(noDisplay: true, sharedDirectories: [],
                                               mount: nil, vncPort: 5999, usbImagePaths: [])
            } else {
                try await vm.run(displayMode: .none, sharedDirectories: [], mount: nil,
                                 vncPort: 5999, vncPassword: "testOnly")
            }
            Issue.record("Expected configuration probe")
        } catch OwnMachineProbe.captured { }
        #expect(captured)
        let export = FileManager.default.temporaryDirectory.appendingPathComponent("lume-config-\(directory.name)")
        #expect(!FileManager.default.fileExists(atPath: export.path))
    }
}
