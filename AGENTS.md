# DOSBox Pure fork maintenance

`retrom-fork.json` fixes the upstream source baseline, EmulatorJS linker, adapter ABI and release assets. `main` mirrors upstream. Retrom changes belong on `retrom/g3a5222c97456`; feature branches start there and merge back after product validation.

Run `.github/rpg-runtime/build-candidate.sh` for the pinned WASM candidate. Keep native DOSBox Pure behavior and existing save compatibility. Do not commit games, BIOS, build outputs or credentials. Retain all upstream and linker license notices.

Release only immutable `retrom-core-g3a5222c97456-rN` tags from commits already merged into the maintenance branch, after PFB review preview, product launch, gamepad, save and new launch restore verification.
