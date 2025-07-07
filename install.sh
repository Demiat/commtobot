#!/bin/sh

set -ex # включить расширенное отображение ошибок

cat /tmp/russian_trusted_root_ca.cer | tee -a $(python -m certifi) &&
apk add --update --no-cache ffmpeg flac &&
rm -rf /var/cache/apk/* &&

exit 0