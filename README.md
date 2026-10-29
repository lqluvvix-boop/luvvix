name: Build APK

on:
  workflow_dispatch:
  push:

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4

      - name: Find mobile app (unzip mobile.zip if needed)
        run: |
          SPEC=$(find . -name buildozer.spec -not -path "*/.buildozer/*" | head -1)
          if [ -z "$SPEC" ] && [ -f mobile.zip ]; then
            unzip -q -o mobile.zip
            SPEC=$(find . -name buildozer.spec -not -path "*/.buildozer/*" | head -1)
          fi
          if [ -z "$SPEC" ]; then
            echo "::error::mobile.zip not found. Upload mobile.zip on the Code tab (Add file - Upload files)."
            exit 1
          fi
          echo "APP_DIR=$(dirname "$SPEC")" >> $GITHUB_ENV
          echo "Found: $SPEC"

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: System packages
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk autoconf automake libtool \
            pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

      - name: Buildozer
        run: pip install --upgrade buildozer cython setuptools

      - name: Cache buildozer
        uses: actions/cache@v4
        with:
          path: ~/.buildozer
          key: buildozer-v1

      - name: Build
        run: |
          cd "$APP_DIR"
          yes | buildozer -v android debug

      - uses: actions/upload-artifact@v4
        with:
          name: luvvix-apk
          path: ${{ env.APP_DIR }}/bin/*.apk
