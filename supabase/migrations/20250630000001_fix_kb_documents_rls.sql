-- Fix kb_documents / kb_chunks RLS
-- Problem: policy "Admins can manage documents" queried auth.users, which authenticated
-- roles cannot read → "permission denied for table users" on SELECT/INSERT via PostgREST.
-- Solution: use public.is_admin_or_manager() (SECURITY DEFINER, already in CRM schema).

DROP POLICY IF EXISTS "Admins can manage documents" ON public.kb_documents;

DROP POLICY IF EXISTS "AI managers can insert kb documents" ON public.kb_documents;
CREATE POLICY "AI managers can insert kb documents"
    ON public.kb_documents
    FOR INSERT
    TO authenticated
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can update kb documents" ON public.kb_documents;
CREATE POLICY "AI managers can update kb documents"
    ON public.kb_documents
    FOR UPDATE
    TO authenticated
    USING (public.is_admin_or_manager())
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can delete kb documents" ON public.kb_documents;
CREATE POLICY "AI managers can delete kb documents"
    ON public.kb_documents
    FOR DELETE
    TO authenticated
    USING (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can manage kb chunks" ON public.kb_chunks;
CREATE POLICY "AI managers can manage kb chunks"
    ON public.kb_chunks
    FOR INSERT
    TO authenticated
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can update kb chunks" ON public.kb_chunks;
CREATE POLICY "AI managers can update kb chunks"
    ON public.kb_chunks
    FOR UPDATE
    TO authenticated
    USING (public.is_admin_or_manager())
    WITH CHECK (public.is_admin_or_manager());

DROP POLICY IF EXISTS "AI managers can delete kb chunks" ON public.kb_chunks;
CREATE POLICY "AI managers can delete kb chunks"
    ON public.kb_chunks
    FOR DELETE
    TO authenticated
    USING (public.is_admin_or_manager());
