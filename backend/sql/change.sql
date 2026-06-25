-- Migrate singular table names to plural table names
-- and add reviews.is_deleted column.

DO $$
BEGIN
    IF to_regclass('public."user"') IS NOT NULL AND to_regclass('public.users') IS NULL THEN
        ALTER TABLE public."user" RENAME TO users;
    END IF;

    IF to_regclass('public.dataset_source') IS NOT NULL AND to_regclass('public.dataset_sources') IS NULL THEN
        ALTER TABLE public.dataset_source RENAME TO dataset_sources;
    END IF;

    IF to_regclass('public.openapi_source') IS NOT NULL AND to_regclass('public.openapi_sources') IS NULL THEN
        ALTER TABLE public.openapi_source RENAME TO openapi_sources;
    END IF;

    IF to_regclass('public.dataset') IS NOT NULL AND to_regclass('public.datasets') IS NULL THEN
        ALTER TABLE public.dataset RENAME TO datasets;
    END IF;

    IF to_regclass('public.collection_dataset') IS NOT NULL AND to_regclass('public.collection_datasets') IS NULL THEN
        ALTER TABLE public.collection_dataset RENAME TO collection_datasets;
    END IF;

    IF to_regclass('public.open_api') IS NOT NULL AND to_regclass('public.open_apis') IS NULL THEN
        ALTER TABLE public.open_api RENAME TO open_apis;
    END IF;

    IF to_regclass('public.collection_openapi') IS NOT NULL AND to_regclass('public.collection_openapis') IS NULL THEN
        ALTER TABLE public.collection_openapi RENAME TO collection_openapis;
    END IF;

    IF to_regclass('public.dataset_chunk') IS NOT NULL AND to_regclass('public.dataset_chunks') IS NULL THEN
        ALTER TABLE public.dataset_chunk RENAME TO dataset_chunks;
    END IF;

    IF to_regclass('public.openapi_chunk') IS NOT NULL AND to_regclass('public.openapi_chunks') IS NULL THEN
        ALTER TABLE public.openapi_chunk RENAME TO openapi_chunks;
    END IF;

    IF to_regclass('public.conversation') IS NOT NULL AND to_regclass('public.conversations') IS NULL THEN
        ALTER TABLE public.conversation RENAME TO conversations;
    END IF;

    IF to_regclass('public.conversation_turn') IS NOT NULL AND to_regclass('public.conversation_turns') IS NULL THEN
        ALTER TABLE public.conversation_turn RENAME TO conversation_turns;
    END IF;

    IF to_regclass('public.dataset_recommendation') IS NOT NULL AND to_regclass('public.dataset_recommendations') IS NULL THEN
        ALTER TABLE public.dataset_recommendation RENAME TO dataset_recommendations;
    END IF;

    IF to_regclass('public.openapi_recommendation') IS NOT NULL AND to_regclass('public.openapi_recommendations') IS NULL THEN
        ALTER TABLE public.openapi_recommendation RENAME TO openapi_recommendations;
    END IF;

    IF to_regclass('public.recommendation') IS NOT NULL AND to_regclass('public.recommendations') IS NULL THEN
        ALTER TABLE public.recommendation RENAME TO recommendations;
    END IF;

    IF to_regclass('public.review') IS NOT NULL AND to_regclass('public.reviews') IS NULL THEN
        ALTER TABLE public.review RENAME TO reviews;
    END IF;

    IF to_regclass('public.bookmark') IS NOT NULL AND to_regclass('public.bookmarks') IS NULL THEN
        ALTER TABLE public.bookmark RENAME TO bookmarks;
    END IF;

    IF to_regclass('public.post') IS NOT NULL AND to_regclass('public.posts') IS NULL THEN
        ALTER TABLE public.post RENAME TO posts;
    END IF;
END $$;

ALTER TABLE IF EXISTS public.reviews
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
