R5.3.1 - Build converter_tool for Vector vSECC
====================================================

Target confirmed from the vSECC diagnostic:
- CPU: armv7l / ARMv7 32-bit
- ABI/libc: armhf + musl 1.2.4
- OS: Alpine Linux 3.18.x
- Persistent path: /data
- /data executable: YES
- Build tools on controller: intentionally not required

Purpose
-------
Build converter_tool OUTSIDE the charger. The GitHub Actions job uses
ARMv7 Alpine 3.18 under QEMU and creates a static musl executable.
Python is only used during cloud build for Designwerk's source generator.
Python is NOT needed on the vSECC at runtime.

How to use
----------
1. Create a new EMPTY GitHub repository (private is OK).
2. Upload the CONTENTS of this ZIP to the repository.
   Important: preserve:
       .github/workflows/build-armv7-musl.yml
3. Open GitHub -> Actions.
4. Choose:
       Build vSECC ARMv7 musl EXI converter
5. Click:
       Run workflow
6. Wait until the job is green.
7. Download artifact:
       vSECC-armv7-musl-converter_tool
8. Extract it on the Windows PC.
9. The file you need is:
       converter_tool
10. In vSECC WebUI -> Container -> Persistent Data,
    upload converter_tool so that Node-RED sees:
       /data/converter_tool
11. Import/run:
       R5_3_STEP3_DECODER_VERIFY_VSECC.json
12. Expected result:
       STATUS=READY_DIN

Do NOT install gcc/cmake/python onto the charger.
Do NOT upload a Windows .exe / x86_64 / ARM64 binary.

After STATUS=READY_DIN
----------------------
Use the included R5.3.1 flow. It is the R5.3 flow changed to use:
    /data/converter_tool

Python on the Windows PC remains ONLY:
    mqtt_capture_to_csv.py

Notes
-----
The cloud build is pinned to Designwerk exi_converter commit:
0ea6122f2ba23fcf5a661c5f418709f642023bb2

The workflow includes a DIN70121 decode smoke test. If that smoke test
fails, GitHub Actions fails and no "ready" artifact should be trusted.
