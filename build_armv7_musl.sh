#!/bin/sh
set -eux

apk add --no-cache \
  bash \
  ca-certificates \
  git \
  build-base \
  cmake \
  python3 \
  py3-pip \
  file

rm -rf /tmp/exi_converter /tmp/exi_build /work/out
mkdir -p /work/out

git clone https://github.com/designwerk-charger/exi_converter.git /tmp/exi_converter
cd /tmp/exi_converter
git checkout 0ea6122f2ba23fcf5a661c5f418709f642023bb2

# Pin the XML schema package to an API generation-era version.
pip3 install --no-cache-dir "xmlschema==1.11.3"

python3 /work/make_standalone_source.py /tmp/exi_converter

cmake -S /tmp/exi_converter -B /tmp/exi_build \
  -DCMAKE_BUILD_TYPE=Release

cmake --build /tmp/exi_build --target converter_tool -- -j2

cp /tmp/exi_build/converter_tool /work/out/converter_tool
chmod 755 /work/out/converter_tool

echo "=== FILE ===" > /work/out/SMOKE_TEST.txt
file /work/out/converter_tool >> /work/out/SMOKE_TEST.txt 2>&1 || true

echo "=== DIN70121 DECODE ===" >> /work/out/SMOKE_TEST.txt
/work/out/converter_tool decode \
  809a021050908c0c0c0c0c51514002808142807c0c0c0000 \
  urn:din:70121:2012:MsgDef \
  >> /work/out/SMOKE_TEST.txt 2>&1

echo "=== PASS ===" >> /work/out/SMOKE_TEST.txt

cd /work/out
sha256sum converter_tool > SHA256SUMS.txt
