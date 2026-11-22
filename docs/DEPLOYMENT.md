# Public dashboard and scheduled ingestion

This optional setup uses **Neon PostgreSQL** for persistent storage, **GitHub Actions** for scheduled imports and **Streamlit Community Cloud** for a public dashboard. It does not use the local Docker database; the remote database starts empty.

## 1. Create a remote PostgreSQL database

1. Create a free Neon project with a PostgreSQL database (check the current plan limits before using it).
2. Copy the database connection URI from Neon's dashboard. Treat it as a secret.
3. Change only the URL scheme from `postgresql://` to `postgresql+psycopg://` for SQLAlchemy's installed psycopg 3 driver. Keep the remaining host, username, password, database and required SSL query parameters unchanged.
4. Do **not** put the URL into code, README, GitHub commits, or screenshots.

The ingestion connection needs rights to create and write table `krakow_hourly`. The dashboard uses the same URL to read data. For a larger deployment, use separate read-only dashboard credentials.

## 2. Configure the daily ingestion job

On GitHub, open this repository's **Settings > Secrets and variables > Actions > New repository secret**. Create a secret named `DATABASE_URL`, containing the complete psycopg 3 URI from step 1.

After merging `.github/workflows/daily-ingest.yml` into `main`, open **Actions > Daily air-quality ingestion > Run workflow**. Select the `main` branch and `14` completed UTC days for the initial import. Check the job's results and database state. On future days the workflow requests the three most recent completed UTC days, which allows delayed data and failed previous runs to be retried safely. Identical observations are not duplicated; changed source values are updated.

The scheduled workflow runs at approximately **07:27 UTC** daily. GitHub may delay or skip a scheduled invocation. Check Actions periodically; a missed or failed run can be recovered with **Run workflow**. Failed requests or unavailable hourly data cause the job to fail visibly; the dashboard displays only stored data.

**Security:** Never post the URI in issues, screenshots or chat. GitHub masks registered secrets in logs, but application code should still avoid logging connection strings. Rotate credentials if accidentally disclosed.

## 3. Publish the dashboard on Streamlit Community Cloud

1. Open [Streamlit Community Cloud](https://share.streamlit.io) and sign in with GitHub.
2. Select **Create app** and use repository `W1CH33R/krakow-air-quality-pipeline`, branch `main`, entrypoint `krakow_air/dashboard.py`.
3. Use Python **3.12** and optionally select a memorable available app subdomain.
4. In **Advanced settings > Secrets**, add this TOML entry using the **same remote database URI** from step 1:

   ```toml
   DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require"
   ```

   This is a placeholder, not a usable credential. Root-level Streamlit secrets are exported as environment variables, so the dashboard's existing `DATABASE_URL` configuration works unchanged. Keep the real URL only in Streamlit Secrets and GitHub Actions Secrets.

5. Deploy the app. It reads Neon PostgreSQL but does not itself import new data. After the GitHub Actions backfill succeeds, refresh the dashboard and select a stored date range.
6. Copy the **real** public app URL into the README and your GitHub repository Website field. Do not add a guessed link beforehand.

`requirements.txt` ensures Streamlit Community Cloud installs this Python project and its runtime dependencies. The dashboard does not require Docker when hosted.

## Troubleshooting

- **No observations yet:** Check that the GitHub Actions backfill ran successfully and that both services use the same remote database URI.
- **Database connection error:** Verify the URI scheme (`postgresql+psycopg://`), Neon credentials, SSL settings and both secret configurations.
- **App cannot import `krakow_air`:** Confirm that the root-level `requirements.txt` is present and that Streamlit Cloud installed the project.
- **Daily job failed:** Read the Actions job logs (avoid copying secrets into reports), then manually re-run the workflow. Data availability from Open-Meteo and GitHub scheduling are external dependencies.

## Limitations

This is a portfolio deployment, not a guaranteed always-on production service. Free plans have quotas and may sleep during inactivity. Hourly values are CAMS model estimates served by Open-Meteo, not direct measurements from individual street-level sensors.
