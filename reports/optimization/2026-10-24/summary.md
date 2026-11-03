# Existing puzzle optimization — 1.2.37

The Android order picker hang was reproduced with actual taps. All popup buttons could enter an infinite parent walk because Kivy Window is its own parent. The shared button now terminates at that root while retaining the guard against releases on a page already left. A bounded subprocess regression covers the actual Popup-to-Window path.

Android emulator taps verified ordinary 3x3, ordinary 4x4 with paint, Pyraminx 4, Mirror 3, and Mixup Plus 4x4x4 after the fix. Screenshots are kept here. The emulator uses x86_64 native libraries; the phone artifact is arm64-v8a. No physical phone was connected.

Mixup now caches model-space surfaces for camera-only redraws. A 100-request sample rebuilt once instead of 100 times (378 surfaces on Mixup 3x3; 960 on Plus 4x4). Painting, composition, rotation and undo invalidate the view cache. Brush changes retain gallery widgets and avoid model redraws. These are geometry timings, not whole-app frame-rate claims.

Checkpoint screen structures are validated before mutating live app state. Android self-check intents now read the Java Activity correctly. Device checks remove stale reports and return failure for incomplete/error reports.

The final targeted suite passed 382 checks with 4 model-specific skips. No puzzle kinds were added. Final package verification lives in reports/package/1.2.37.
