--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4 (Postgres.app)
-- Dumped by pg_dump version 16.4 (Postgres.app)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: user; Type: TABLE; Schema: un0; Owner: un0_test_user_admin
--

CREATE TABLE un0."user" (
    email character varying(255) NOT NULL,
    handle character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    tenant_id character varying(26),
    default_group_id character varying(26),
    is_superuser boolean DEFAULT false NOT NULL,
    is_tenant_admin boolean DEFAULT false NOT NULL,
    id character varying(26) DEFAULT un0.generate_ulid() NOT NULL,
    related_object_id character varying(26),
    is_active boolean DEFAULT true NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    modified_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp with time zone,
    import_id bigint,
    import_key character varying,
    CONSTRAINT user_ck_user_is_superuser_check CHECK ((((is_superuser = false) AND (is_tenant_admin = false)) OR ((is_superuser = true) AND (is_tenant_admin = false)) OR ((is_superuser = false) AND (is_tenant_admin = true))))
);

ALTER TABLE ONLY un0."user" FORCE ROW LEVEL SECURITY;


ALTER TABLE un0."user" OWNER TO un0_test_user_admin;

--
-- Name: TABLE "user"; Type: COMMENT; Schema: un0; Owner: un0_test_user_admin
--

COMMENT ON TABLE un0."user" IS 'Application users';


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: un0; Owner: un0_test_user_admin
--

ALTER TABLE ONLY un0."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: un0_user_default_group_id_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE INDEX un0_user_default_group_id_idx ON un0."user" USING btree (default_group_id);


--
-- Name: un0_user_email_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE UNIQUE INDEX un0_user_email_idx ON un0."user" USING btree (email);


--
-- Name: un0_user_handle_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE UNIQUE INDEX un0_user_handle_idx ON un0."user" USING btree (handle);


--
-- Name: un0_user_id_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE INDEX un0_user_id_idx ON un0."user" USING btree (id);


--
-- Name: un0_user_is_superuser_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE INDEX un0_user_is_superuser_idx ON un0."user" USING btree (is_superuser);


--
-- Name: un0_user_is_tenant_admin_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE INDEX un0_user_is_tenant_admin_idx ON un0."user" USING btree (is_tenant_admin);


--
-- Name: un0_user_related_object_id_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE UNIQUE INDEX un0_user_related_object_id_idx ON un0."user" USING btree (related_object_id);


--
-- Name: un0_user_tenant_id_idx; Type: INDEX; Schema: un0; Owner: un0_test_user_admin
--

CREATE INDEX un0_user_tenant_id_idx ON un0."user" USING btree (tenant_id);


--
-- Name: user audit_i_u_d; Type: TRIGGER; Schema: un0; Owner: un0_test_user_admin
--

CREATE TRIGGER audit_i_u_d AFTER INSERT OR DELETE OR UPDATE ON un0."user" FOR EACH ROW EXECUTE FUNCTION audit.insert_update_delete_trigger();


--
-- Name: user audit_t; Type: TRIGGER; Schema: un0; Owner: un0_test_user_admin
--

CREATE TRIGGER audit_t AFTER TRUNCATE ON un0."user" FOR EACH STATEMENT EXECUTE FUNCTION audit.truncate_trigger();


--
-- Name: user user_delete_vertex_trigger; Type: TRIGGER; Schema: un0; Owner: un0_test_user_admin
--

CREATE TRIGGER user_delete_vertex_trigger AFTER DELETE ON un0."user" FOR EACH ROW EXECUTE FUNCTION un0.user_delete_vertex();


--
-- Name: user user_insert_vertex_trigger; Type: TRIGGER; Schema: un0; Owner: un0_test_user_admin
--

CREATE TRIGGER user_insert_vertex_trigger AFTER INSERT ON un0."user" FOR EACH ROW EXECUTE FUNCTION un0.user_insert_vertex();


--
-- Name: user user_truncate_vertex_trigger; Type: TRIGGER; Schema: un0; Owner: un0_test_user_admin
--

CREATE TRIGGER user_truncate_vertex_trigger AFTER TRUNCATE ON un0."user" FOR EACH STATEMENT EXECUTE FUNCTION un0.user_truncate_vertex();


--
-- Name: user user_update_vertex_trigger; Type: TRIGGER; Schema: un0; Owner: un0_test_user_admin
--

CREATE TRIGGER user_update_vertex_trigger AFTER UPDATE ON un0."user" FOR EACH ROW EXECUTE FUNCTION un0.user_update_vertex();


--
-- Name: user user_default_group_id_fkey; Type: FK CONSTRAINT; Schema: un0; Owner: un0_test_user_admin
--

ALTER TABLE ONLY un0."user"
    ADD CONSTRAINT user_default_group_id_fkey FOREIGN KEY (default_group_id) REFERENCES un0."group"(id) ON DELETE SET NULL;


--
-- Name: user user_related_object_id_fkey; Type: FK CONSTRAINT; Schema: un0; Owner: un0_test_user_admin
--

ALTER TABLE ONLY un0."user"
    ADD CONSTRAINT user_related_object_id_fkey FOREIGN KEY (related_object_id) REFERENCES un0.related_object(id) ON DELETE CASCADE;


--
-- Name: user user_tenant_id_fkey; Type: FK CONSTRAINT; Schema: un0; Owner: un0_test_user_admin
--

ALTER TABLE ONLY un0."user"
    ADD CONSTRAINT user_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES un0.tenant(id) ON DELETE CASCADE;


--
-- Name: user; Type: ROW SECURITY; Schema: un0; Owner: un0_test_user_admin
--

ALTER TABLE un0."user" ENABLE ROW LEVEL SECURITY;

--
-- Name: user user_delete_policy; Type: POLICY; Schema: un0; Owner: un0_test_user_admin
--

CREATE POLICY user_delete_policy ON un0."user" FOR DELETE USING (((current_setting('s_var.is_superuser'::text, true))::boolean));


--
-- Name: user user_insert_policy; Type: POLICY; Schema: un0; Owner: un0_test_user_admin
--

CREATE POLICY user_insert_policy ON un0."user" FOR INSERT WITH CHECK (((current_setting('s_var.is_superuser'::text, true))::boolean));


--
-- Name: user user_select_policy; Type: POLICY; Schema: un0; Owner: un0_test_user_admin
--

CREATE POLICY user_select_policy ON un0."user" FOR SELECT USING (((current_setting('s_var.is_superuser'::text, true))::boolean OR ((tenant_id)::text = ((current_setting('s_var.tenant_id'::text, true))::character varying(26))::text)));


--
-- Name: user user_update_policy; Type: POLICY; Schema: un0; Owner: un0_test_user_admin
--

CREATE POLICY user_update_policy ON un0."user" FOR UPDATE WITH CHECK (((current_setting('s_var.is_superuser'::text, true))::boolean));


--
-- Name: TABLE "user"; Type: ACL; Schema: un0; Owner: un0_test_user_admin
--

GRANT SELECT ON TABLE un0."user" TO un0_test_user_reader;
GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE un0."user" TO un0_test_user_writer;


--
-- PostgreSQL database dump complete
--
