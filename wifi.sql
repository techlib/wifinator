--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: profile_overlap_check_fn(); Type: FUNCTION; Schema: public; Owner: wifi
--

CREATE FUNCTION profile_overlap_check_fn() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
 cnt INT;

BEGIN

 SELECT count(*) INTO cnt FROM profile
 WHERE tsrange(NEW.start, NEW.stop) && tsrange(start, stop) AND id != NEW.id;

 IF cnt >= 4 THEN
  RAISE EXCEPTION 'too many overlapping profiles';
 END IF;

 SELECT count(*) INTO cnt FROM profile
 WHERE tsrange(NEW.start, NEW.stop) && tsrange(start, stop) AND
       NEW.id != id AND
       NEW.ssid = ssid;

 IF cnt > 0 THEN
  RAISE EXCEPTION 'overlapping SSIDs';
 END IF;

 RETURN NEW;

END;
$$;


ALTER FUNCTION public.profile_overlap_check_fn() OWNER TO wifi;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: audit; Type: TABLE; Schema: public; Owner: wifi; Tablespace: 
--

CREATE TABLE audit (
    id integer NOT NULL,
    profile integer,
    old_data json,
    new_data json,
    "time" timestamp with time zone NOT NULL,
    "user" text NOT NULL
);


ALTER TABLE public.audit OWNER TO wifi;

--
-- Name: audit_id_seq; Type: SEQUENCE; Schema: public; Owner: wifi
--

CREATE SEQUENCE audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.audit_id_seq OWNER TO wifi;

--
-- Name: audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wifi
--

ALTER SEQUENCE audit_id_seq OWNED BY audit.id;


--
-- Name: profile; Type: TABLE; Schema: public; Owner: wifi; Tablespace: 
--

CREATE TABLE profile (
    id integer NOT NULL,
    ssid character varying(30) COLLATE pg_catalog."C" NOT NULL,
    psk character varying(30) COLLATE pg_catalog."C" NOT NULL,
    start timestamp without time zone NOT NULL,
    stop timestamp without time zone NOT NULL,
    CONSTRAINT profile_psk_min_length CHECK ((char_length((psk)::text) >= 8)),
    CONSTRAINT profile_ssid_length CHECK ((char_length((ssid)::text) > 0)),
    CONSTRAINT profile_ssid_reserved CHECK ((substr((ssid)::text, 1, 12) <> 'NTK-RoboAkce'::text)),
    CONSTRAINT profile_stop_after_start CHECK ((stop >= start))
);


ALTER TABLE public.profile OWNER TO wifi;

--
-- Name: profile_id_seq; Type: SEQUENCE; Schema: public; Owner: wifi
--

CREATE SEQUENCE profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.profile_id_seq OWNER TO wifi;

--
-- Name: profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: wifi
--

ALTER SEQUENCE profile_id_seq OWNED BY profile.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: wifi
--

ALTER TABLE ONLY audit ALTER COLUMN id SET DEFAULT nextval('audit_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: wifi
--

ALTER TABLE ONLY profile ALTER COLUMN id SET DEFAULT nextval('profile_id_seq'::regclass);


--
-- Name: audit_pkey; Type: CONSTRAINT; Schema: public; Owner: wifi; Tablespace: 
--

ALTER TABLE ONLY audit
    ADD CONSTRAINT audit_pkey PRIMARY KEY (id);


--
-- Name: profile_pkey; Type: CONSTRAINT; Schema: public; Owner: wifi; Tablespace: 
--

ALTER TABLE ONLY profile
    ADD CONSTRAINT profile_pkey PRIMARY KEY (id);


--
-- Name: fki_audit_profile_fkey; Type: INDEX; Schema: public; Owner: wifi; Tablespace: 
--

CREATE INDEX fki_audit_profile_fkey ON audit USING btree (profile);


--
-- Name: profile_start_idx; Type: INDEX; Schema: public; Owner: wifi; Tablespace: 
--

CREATE INDEX profile_start_idx ON profile USING btree (start);


--
-- Name: profile_stop_idx; Type: INDEX; Schema: public; Owner: wifi; Tablespace: 
--

CREATE INDEX profile_stop_idx ON profile USING btree (stop);


--
-- Name: profile_overlap_check; Type: TRIGGER; Schema: public; Owner: wifi
--

CREATE CONSTRAINT TRIGGER profile_overlap_check AFTER INSERT OR UPDATE ON profile DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE PROCEDURE profile_overlap_check_fn();


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

