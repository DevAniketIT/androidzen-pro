# Device Lab Runbook

Purpose: Manage the Android device farm covering versions 10-15 across Samsung, Google, Motorola, Xiaomi, OnePlus. Supports both device owner and work profile modes.

References
- Device matrix: infrastructure/device-lab/device-matrix.yaml
- Service integrations: infrastructure/device-lab/service-integrations.yaml
- Credentials: infrastructure/credentials/credentials-inventory.yaml

Physical device setup
1) Device enrollment
- Power up device; complete OOB setup
- Enable developer mode: tap Build number 7x
- Enable ADB/USB debugging; pair with adb wireless where supported
- For ZTE devices: enroll via Google Zero Touch using production configs

2) Configuration per matrix
- Apply device owner profile using DPC (com.androidzen.dpc)
- Or create managed work profile for BYOD scenarios
- Install test apps per requirements
- Record device serial, endpoint IP in matrix yaml

Health monitoring
- Status checks via adb shell getprop sys.boot_completed every 5m
- Battery level checks; charge if <20%; pause tests if <15%
- Temperature warnings >45°C; critical alerts >60°C
- Storage monitoring; free space alerts <1GB

ADB debugging
- Check connectivity: adb devices -l
- Restart daemon: adb kill-server; adb start-server
- Wireless: adb connect 192.168.1.XXX:5555
- Log collection: adb logcat -d > device-logs.txt

Remote control gateway
- TeamViewer QuickSupport installed on select devices
- Chrome Remote Desktop for development access
- VNC server on Linux hosts for emulators

EMM integrations testing
- Zero Touch: factory reset test devices; verify auto-enrollment
- Managed Play: app install/remove/permissions via Play Console
- FCM: test push messages delivery; measure latency

Test execution
- Device selection: filter by Android version, OEM, work profile availability
- Parallel execution: max 5 per physical device for performance
- Results collection: screenshots, logcat, performance metrics
- Clean up: uninstall test apps; restore to baseline state

Network conditions
- TC netem: simulate latency, jitter, packet loss
- Captive portals: redirect traffic to auth pages
- Proxy: corporate HTTP proxy with authentication
- Metered: throttle bandwidth; data usage warnings

Provisioning new devices
- Purchase/acquire device as per OEM requirements
- Set up per matrix specifications
- Register in asset management
- Add to CI configuration
- Document location (rack-X-slot-Y)

Exit criteria verification
- All devices reachable by CI jobs: adb devices shows Online
- Health checks: green status for battery, storage, connectivity
- Pilot enrollments: successful for both device owner and work profile
- Remote commands: basic commands (getprop, dumpsys) succeed within 10s timeout
