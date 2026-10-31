#!/usr/bin/env bash
# Install Google's EGM plugin for this project only.
# Needs Claude Code 2.1.271 or later (the reviewers rely on omitClaudeMd).
claude plugin marketplace add google/elephant-goldfish-model
claude plugin install egm@egm --scope project

# Start a new Claude Code session now, so the plugin loads.
# The commands then show up with the /egm: prefix.

# Uninstall (run from the same project folder):
# claude plugin uninstall egm@egm --scope project
# claude plugin marketplace remove egm
