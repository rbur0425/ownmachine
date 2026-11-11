# Retrieve your private viewer link

Run the access helper **on the machine running the viewer, as its owner**, from
an up-to-date source checkout. Python's standard library is enough; it does not
need the Hermes or noVNC environment. Use the same shared control directory as
the viewer (the host bind-mount path when Hermes runs in Docker).

```sh
python3 scripts/ownmachine-viewer-access.py \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine"
```

The default prints authenticated availability and the actual listener port,
without printing the credential. To retrieve the link in your private terminal:

```sh
python3 scripts/ownmachine-viewer-access.py \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine" --show-url
```

Open the returned link. Alternatively use `--show-token` and paste its output
into the viewer's unlock form. These explicit options print a bearer credential;
keep terminal output private and do not paste it into an agent prompt, support
report, CI log or repository. The helper never stores a copy, opens a browser,
changes clipboard contents or grants human control.

## When the viewer runs remotely

Log into the viewer server using your own verified SSH configuration, then run:

```sh
python3 scripts/ownmachine-viewer-access.py \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine" \
  --ssh-target viewer-server --local-port 45678
```

Replace `viewer-server` with the SSH alias **your local computer** uses to reach
that server. This prints, but never executes, an SSH forwarding command. Run the
printed command in a terminal on your local computer and leave it running. It
binds only local loopback and refuses a forwarding failure. Choose another
available local port if necessary; the helper cannot inspect your computer's
ports from the server.

Back on the viewer server, retrieve a matching link:

```sh
python3 scripts/ownmachine-viewer-access.py \
  --access-dir "$HOME/.local/state/ownmachine-viewer/ownmachine" \
  --local-port 45678 --show-url
```

Open that link on your local computer. `--local-port` changes only the displayed
link/tunnel endpoint. The authenticated check always uses the actual viewer
listener recorded in its private access file. It never reconfigures the viewer.
Omit `--local-port` to use the actual viewer port at both ends. Request the tunnel
command separately from secret output to keep it safe to copy into a shell.

## Recovery and limits

Every retrieval first validates the owner-only regular access file and sends an
authenticated read to the numeric loopback listener. Symlinks, unsafe permissions,
non-loopback destinations, redirects and failed authentication are refused.
HTTP proxy settings are ignored. Errors omit raw response bodies and credentials.
Use `--timeout-seconds` (1–120, default 10) to bound socket operations.

Restarting the viewer rotates its token and may change its port. Rerun the helper,
update the tunnel if necessary, and open the new link. A viewer can stop or rotate
after a successful check; the helper does not promise continued availability.
For failures, use [viewer doctor](recovery.md). Retrieval does not test the browser
stream, inspect the desktop, transfer control, clear uncertainty, restart a VM,
or certify the host firewall. Reserve human control explicitly in the viewer.

The access directory is private to the separate viewer user and must be outside
the shared control tree. See [identity separation](security-isolation.md).
