# Heroku Deployment

This project deploys to Heroku as two container apps:

- `brightsolar-api` - FastAPI backend + Heroku Postgres
  - URL: `https://brightsolar-api-e82e91ff036a.herokuapp.com`
- `brightsolar-ops` - Next.js frontend
  - URL: `https://brightsolar-ops-ba7171217395.herokuapp.com`

Heroku does not run this repo's Docker Compose stack directly. Each app is
deployed from its subdirectory with its own `heroku.yml`.

## One-Time Setup

```bash
heroku login

heroku create brightsolar-api --stack container
heroku addons:create heroku-postgresql:essential-0 -a brightsolar-api
heroku config:set ENV=production JWT_SECRET="$(openssl rand -hex 32)" -a brightsolar-api

heroku create brightsolar-ops --stack container
heroku config:set NEXT_PUBLIC_API_URL=https://brightsolar-api-e82e91ff036a.herokuapp.com -a brightsolar-ops
heroku config:set CORS_ORIGINS=https://brightsolar-ops-ba7171217395.herokuapp.com -a brightsolar-api
```

## Deploy

```bash
git subtree push --prefix backend https://git.heroku.com/brightsolar-api.git main
git subtree push --prefix frontend https://git.heroku.com/brightsolar-ops.git main
```

Then seed the first data set:

```bash
heroku run python -m app.seed -a brightsolar-api
```

## Verify

```bash
heroku open -a brightsolar-ops
heroku logs --tail -a brightsolar-api
heroku logs --tail -a brightsolar-ops
```

## Important Heroku Caveat

Heroku dyno filesystems are ephemeral. Receipt uploads stored under `/app/uploads`
can disappear when dynos restart. For production receipt retention, add S3 or
another persistent object store before relying on receipt uploads.
