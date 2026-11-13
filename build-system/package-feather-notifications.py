import argparse
import plistlib
import re
import struct
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def package(source, service_executable, output, build_number):
    with ZipFile(source) as ipa:
        members = set(ipa.namelist())
        app_plist, = (
            name for name in members
            if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", name)
        )
        app = str(PurePosixPath(app_plist).parent)
        if any(name.startswith(f"{app}/PlugIns/") for name in members):
            raise ValueError("Expected the standalone Feather IPA")

        app_info = plistlib.loads(ipa.read(app_plist))
        if (app_info.get("GhostgramStandaloneStorage") is not True
                or app_info["CFBundleIdentifier"] != "org.ghostgram.sideload"):
            raise ValueError("Unexpected Ghostgram storage mode or bundle identifier")

        binary = service_executable.read_bytes()
        if struct.unpack_from("<II", binary) != (0xFEEDFACF, 0x0100000C):
            raise ValueError("The notification extension must be an arm64 Mach-O")

        executable_name = "FeatherNotificationService"
        extension = f"{app}/PlugIns/{executable_name}.appex"
        extension_info = {
            key: app_info[key] for key in (
                "CFBundleDevelopmentRegion", "CFBundleSupportedPlatforms", "DTPlatformName",
                "DTSDKName", "MinimumOSVersion", "UIDeviceFamily",
            ) if key in app_info
        }
        extension_info.update({
            "CFBundleExecutable": executable_name,
            "CFBundleIdentifier": app_info["CFBundleIdentifier"] + ".NotificationService",
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": "Ghostgram",
            "CFBundlePackageType": "XPC!",
            "CFBundleShortVersionString": app_info["CFBundleShortVersionString"],
            "CFBundleVersion": build_number,
            "NSExtension": {
                "NSExtensionPointIdentifier": "com.apple.usernotifications.service",
                "NSExtensionPrincipalClass": executable_name,
            },
        })
        app_info["CFBundleVersion"] = build_number

        with ZipFile(output, "w", compression=ZIP_DEFLATED) as result:
            for entry in ipa.infolist():
                if "/_CodeSignature/" in entry.filename or entry.filename.endswith("/embedded.mobileprovision"):
                    continue
                if entry.filename == app_plist:
                    result.writestr(entry, plistlib.dumps(app_info, fmt=plistlib.FMT_BINARY))
                else:
                    result.writestr(entry, ipa.read(entry))
            result.writestr(f"{extension}/Info.plist", plistlib.dumps(extension_info, fmt=plistlib.FMT_BINARY))
            executable = ZipInfo(f"{extension}/{executable_name}")
            executable.create_system = 3
            executable.external_attr = 0o100755 << 16
            result.writestr(executable, binary, compress_type=ZIP_DEFLATED)

    with ZipFile(output) as result:
        failed_member = result.testzip()
        if failed_member:
            raise ValueError(f"Damaged output member: {failed_member}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a notification service to the standalone Feather IPA")
    parser.add_argument("source", type=Path)
    parser.add_argument("service_executable", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("build_number")
    args = parser.parse_args()
    package(args.source, args.service_executable, args.output, args.build_number)
