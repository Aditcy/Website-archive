# Architecture

FastAPI provides the API and dashboard. PostgreSQL is the durable repository. Redis/Celery provides persistent background jobs. Discovery uses robots.txt, sitemap XML, HTML links, canonical links and feeds. URLs are normalized and deduplicated by domain. Crawl state is stored in PostgreSQL so interrupted work can resume. Archive services use provider adapters. Wayback uses Save Page Now when credentials are configured. Archive.today is represented as a manual provider until a documented public automated submission interface is verified.

Core flow:

domain -> crawl -> URL repository -> submission queue -> archive provider -> submission history
