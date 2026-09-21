# Vector Databases

A vector store needs deterministic IDs, upsert semantics, metadata filters, deletion support, and an inspectable source record. Abstract it behind a small interface so local tests do not require a hosted service.

Plan for tenant isolation, encryption, backups, index rebuilds, stale-document removal, and query observability. A collection existing does not prove ingestion completed successfully.
