# Running the scheduled worker

The worker is a one-shot container: it runs the ADK workflow once and exits.
It does not include a scheduler or an API server. ADK telemetry is disabled
in the image so the worker can run without an interactive consent prompt.

1. Install Podman and a Podman Compose provider on the Mac mini.
2. Create `goodreads_agent/.env` with the runtime configuration, including
   `HARDCOVER_APP_API_KEY`, `HARDCOVER_APP_API_URL`, `BUFFER_ACCESS_TOKEN`,
   and the Google authentication settings used by ADK. The worker's
   `NEO4J_URL` is set by Compose to the Neo4j service hostname. If
   `NEO4J_USERNAME`, `NEO4J_PASSWORD`, or `NEO4J_DATABASE` are set in this
   file, they must match the Neo4j service configuration.
3. From the project directory, start Neo4j and run the worker:

   ```sh
   podman compose up -d neo4j
   podman compose run --rm --build worker
   ```

The worker profile keeps it from starting during a normal `compose up`. The
Compose dependency waits for the Neo4j health check when supported by the
installed Compose provider. Neo4j data persists in the `neo4j_data` volume.
The environment file is supplied at runtime and excluded from the image.
If `BUFFER_ACCESS_TOKEN` is missing or `GOODREADS_BACKFILL` is set, the worker
uses stub mode; the stub output is lost when the `--rm` container is removed.

Use macOS `launchd` or another host scheduler to run
`podman compose run --rm worker` at the desired interval, from this project
directory, after building the image. Ensure scheduled runs cannot overlap and
capture their output and failures. No scheduler is configured by this setup.

**Before enabling unattended runs:** the workflow currently saves its last-run
timestamp before posting and persistence complete. A later failure can cause
activities to be skipped, and partial Buffer delivery is not tracked per
channel. Resolve these reliability issues before relying on retries. Also,
the existing Compose file uses a development Neo4j password; replace it with a
secure runtime configuration before deployment.