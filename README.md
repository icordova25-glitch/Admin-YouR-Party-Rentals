# Admin-YouR-Party-Rentals

Admin website and Python backend for YouR Party Rentals LLC.

## Temporary Login

- Username: `admin`
- Password: `yourr-admin`

After signing in, use **Admin Login Credentials** to set a new username and password. The active credentials are stored server-side in `data/admin-auth.json`, which is ignored by Git. Never commit that file.

## Run locally

```sh
python3 server.py
```

Open `http://localhost:3002/admin-gallery.html`.

## Vercel deployment

The static admin page can be deployed to Vercel, but the Python `server.py` process is not automatically run by a static Vercel deployment. The authenticated API features require a Python-compatible host or a Vercel serverless function conversion. For local use, run `python3 server.py`.
