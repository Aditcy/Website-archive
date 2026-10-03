CREATE INDEX IF NOT EXISTS ix_urls_domain_norm ON urls(domain_id,norm_url);
CREATE INDEX IF NOT EXISTS ix_sub_status_service ON submissions(status,service);
