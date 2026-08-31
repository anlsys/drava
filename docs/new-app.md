# Writing and adding a Drava app

A Drava stage is a callback plus one call to `drava.run`. The runtime owns the
stream lifecycle — it strips the end-of-stream (EOS) marker before your callback
runs, tracks each frame's global position, drives finalization once the stream
drains, and forwards EOS to the next stage — so your callback only handles data.

## Writing a stage callback

```python
import drava

def func(frames, base_index):
    # frames: list[bytes] of data payloads (no EOS marker)
    # base_index: global index of frames[0] across the whole stream
    for i, raw in enumerate(frames):
        result = process(raw)
        drava.publish_py(result)   # transform stages publish downstream

drava.run(func)
```

- Callbacks may be `func(frames)` or `func(frames, base_index)`; `drava.run`
  adapts either.
- For a **terminal** stage that produces a final result, pass an
  `on_end_of_stream` hook and set `egress.forward_eos: false` in `pipeline.yaml`:

  ```python
  def finalize(expected_frames):
      write_output()          # runs once, after all callbacks drain

  drava.run(func, on_end_of_stream=finalize)
  ```

- Concurrency: with `callback_serialize: false` the runtime runs callbacks on
  multiple threads. Because the runtime owns EOS accounting and `base_index`, a
  stateless callback needs no lock. Keep app-side locks only for state the app
  itself accumulates (e.g. a result list).
- The app callback must **not** parse the `DRAVA_EOS:` marker — the runtime owns
  EOS. Publishers (the data source) still emit it.

## Adding a new example app

A new app needs only a **callback** (`app.py`) and a **`pipeline.yaml`**;
everything generic (config parsing, the publisher loop, EOS, metrics) comes from
[examples/common](../examples/common). The quickest start is to copy an existing
example (`examples/iris_knn` for one stage, `examples/ptychonn` for two) and
adapt it.

1. **Write `app.py`** — the stage callback (above).

2. **Write `pipeline.yaml`** — set `transport.type`, each stage's
   `runtime.threads` / `callback_batch`, and the `ingress`/`egress`
   stream/subject names. For a multi-stage pipeline, **stage N's `egress` must
   match stage N+1's `ingress`**:

   ```yaml
   pipeline:
     name: myapp
   transport:
     type: nats
     nats_url: nats://127.0.0.1:4222
   stages:
     - name: stage1
       runtime: { threads: 4, callback_batch: 256 }
       ingress: { stream: FRAMES, subject: frames.raw, durable: s1 }
       egress:  { stream: OUT, subject: frames.stage1 }
     - name: stage2
       runtime: { threads: 4, callback_batch: 256 }
       ingress: { stream: OUT, subject: frames.stage1, durable: s2 }
       egress:  { forward_eos: false }        # terminal stage
   ```

3. **Add a publisher** — the data source is the only app-specific publisher part.
   Reuse the shared loop from `drava_common`:

   ```python
   import asyncio, os, sys
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "common"))
   from drava_common import (connect_jetstream, load_transport_config,
                             load_publish_config, publish_stream)

   def make_payload(i: int) -> bytes:
       ...                                  # your bytes for frame i

   async def main():
       url, stream, subject = load_transport_config()
       rate_hz, synthetic, num_frames = load_publish_config()
       js = await connect_jetstream(url, stream, subject)
       await publish_stream(js, subject, make_payload, num_frames, rate_hz=rate_hz)

   asyncio.run(main())
   ```

   For the socket transport, use `socket_publish_stream` (see
   `examples/ptychonn/publisher_socket.py`).

4. **Run it** as in [docs/examples.md](examples.md) (one process per stage plus
   the publisher), or with the [`drava-pipeline`](utils.md) helper.

## Modifying an existing app

- Change **runtime behavior** (threads, batch size, transport, stream names, EOS
  forwarding) in the stage's `pipeline.yaml` — not in code. The runtime reads
  these from YAML.
- Change **computation** in the stage callback (`app.py` / `app_stageN.py`).
- Change the **data source** (payload contents, rate, frame count) in the
  example's publisher / `publisher_util.py`; generic pacing/EOS/metrics stay in
  `drava_common`.
- Keep example-specific code minimal and shared helpers in `drava_common`, not
  per-example copies. Retired code goes in an `archive/` subfolder of the example.

## Conventions the runtime relies on

- EOS is runtime-owned; callbacks never parse `DRAVA_EOS:`.
- Metrics go to files, not stdout (see the
  [Metrics section of the README](../README.md#metrics-and-energy)).
- `pipeline.yaml` is authoritative for runtime knobs.
