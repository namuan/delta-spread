#!/usr/bin/env bash
APP_BUNDLE=$1
rm -rf "$HOME/Applications/${APP_BUNDLE}"
mv "./dist/${APP_BUNDLE}" "$HOME/Applications"
