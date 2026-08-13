#!/bin/bash
echo delete_log Start
find log -name jackbot.log* -mtime +30 -delete 2>/dev/null || true
echo done
