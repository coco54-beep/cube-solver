# 1.2.37 package verification

Android arm64 APK and Windows portable ZIP built successfully. APK version and signature are verified; its signing certificate matches 1.2.36. 743 application bytecode/data files match the captured Android sources. Windows self-check and ZIP CRC pass; five modified Windows modules match current source bytecode.

The exact delivered private.tar application payload was exercised in an x86_64 Android runtime with matching Python bytecode ABI. Fresh launch, actual taps through the order popup into 2x2, and colouring succeeded without injected source patches. A new intent-triggered page check passed 15 pages. Earlier manual taps also covered 3x3, 4x4, Pyraminx 4, Mirror 3 and Mixup Plus 4 after the same shared button fix. No physical arm64 phone was connected.

382 targeted regression checks passed, 4 model-specific cases skipped. Optimization details are in reports/optimization/2026-10-24.
