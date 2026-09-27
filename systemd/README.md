# Running it on the Pi

    sudo cp systemd/scraper.service systemd/scraper.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now scraper.timer

Check it:

    systemctl list-timers scraper.timer     # when it last ran, when it runs next
    journalctl -u scraper.service -n 50     # what happened last time
    cat logs/run-*.log                      # the same, kept per run

## Why a timer rather than cron

cron fires only if the machine is awake at the appointed minute. This one is
at home — power cuts, unplugging, router reboots — and every one of those used
to mean a month silently missing.

`Persistent=true` records when the run was last due. If the Pi was off, the run
starts when it comes back instead of waiting for next month.

## Testing it without waiting a month

    sudo systemctl start scraper.service    # run it now
    journalctl -u scraper.service -f

The push refuses to send an empty snapshot and confirms the row count on the
droplet afterwards, so a test run cannot quietly push nothing. If a snapshot
has already been confirmed delivered it exits without resending — delete
`.last_delivered` to force one.
