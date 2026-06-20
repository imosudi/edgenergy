#!/bin/sh
set -e

echo "Updating apt package list..."
apt-get update -y
echo "Installing librsvg2-bin..."
apt-get install -y --no-install-recommends librsvg2-bin

# Make sure output directories exist
mkdir -p docs
mkdir -p edge/dashboard

echo "Converting EdgeNergy.svg (Logo) to various sizes..."
rsvg-convert -o docs/logo_16x16.png -w 16 -h 16 EdgeNergy.svg
rsvg-convert -o docs/logo_32x32.png -w 32 -h 32 EdgeNergy.svg
rsvg-convert -o docs/logo_48x48.png -w 48 -h 48 EdgeNergy.svg
rsvg-convert -o docs/logo_128x128.png -w 128 -h 128 EdgeNergy.svg
rsvg-convert -o docs/logo_192x192.png -w 192 -h 192 EdgeNergy.svg
rsvg-convert -o docs/logo_512x512.png -w 512 -h 512 EdgeNergy.svg

echo "Converting logo.svg (Banner) to various sizes..."
rsvg-convert -o docs/banner_1200x360.png -w 1200 -h 360 logo.svg
rsvg-convert -o docs/banner_800x240.png -w 800 -h 240 logo.svg

echo "Copying web-app icons to dashboard folder..."
cp docs/logo_32x32.png edge/dashboard/favicon.png
cp docs/logo_192x192.png edge/dashboard/icon_192.png
cp docs/logo_512x512.png edge/dashboard/icon_512.png

echo "Image conversion completed successfully!"
ls -lh docs/
