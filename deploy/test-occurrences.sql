--
-- PostgreSQL database dump
--

\restrict b6eowmSwAxKiH95gn3MRUq6Tn1K5rSeaborfm2CJkDd08U88gsMGKVbXcRwiiPp

-- Dumped from database version 17.10 (Debian 17.10-1.pgdg13+1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
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
-- Name: ocorrencias_stg; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocorrencias_stg (
    nome_departamento text,
    nome_seccional text,
    nome_delegacia text,
    nome_municipio text,
    num_bo text,
    ano_bo smallint,
    data_registro date,
    data_ocorrencia_bo date,
    hora_ocorrencia_bo text,
    desc_periodo text,
    descr_tipolocal text,
    descr_subtipolocal text,
    bairro text,
    logradouro text,
    numero_logradouro text,
    latitude double precision,
    longitude double precision,
    nome_delegacia_circunscricao text,
    nome_departamento_circunscricao text,
    nome_seccional_circunscricao text,
    nome_municipio_circunscricao text,
    rubrica text,
    descr_conduta text,
    natureza_apurada text,
    mes_estatistica smallint,
    ano_estatistica smallint,
    cmd text,
    btl text,
    cia text,
    cod_ibge integer,
    geom public.geometry(Point,4326),
    id integer NOT NULL,
    bairro_normalizado text,
    geog public.geography(Point,4326)
);


--
-- Name: ocorrencias_stg_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ocorrencias_stg_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ocorrencias_stg_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ocorrencias_stg_id_seq OWNED BY public.ocorrencias_stg.id;


--
-- Name: ocorrencias_stg id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencias_stg ALTER COLUMN id SET DEFAULT nextval('public.ocorrencias_stg_id_seq'::regclass);


--
-- Name: ocorrencias_stg ocorrencias_stg_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocorrencias_stg
    ADD CONSTRAINT ocorrencias_stg_pkey PRIMARY KEY (id);


--
-- Name: idx_bairro_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bairro_trgm ON public.ocorrencias_stg USING gin (bairro_normalizado public.gin_trgm_ops);


--
-- Name: idx_ocorrencias_ano; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_ano ON public.ocorrencias_stg USING btree (ano_estatistica);


--
-- Name: idx_ocorrencias_bairro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_bairro ON public.ocorrencias_stg USING btree (bairro_normalizado);


--
-- Name: idx_ocorrencias_cod_ibge; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_cod_ibge ON public.ocorrencias_stg USING btree (cod_ibge);


--
-- Name: idx_ocorrencias_data; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_data ON public.ocorrencias_stg USING btree (data_ocorrencia_bo);


--
-- Name: idx_ocorrencias_geog; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_geog ON public.ocorrencias_stg USING gist (geog);


--
-- Name: idx_ocorrencias_ibge_ano; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_ibge_ano ON public.ocorrencias_stg USING btree (cod_ibge, ano_estatistica);


--
-- Name: idx_ocorrencias_municipio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_municipio ON public.ocorrencias_stg USING btree (nome_municipio);


--
-- Name: idx_ocorrencias_municipio_ano; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_municipio_ano ON public.ocorrencias_stg USING btree (nome_municipio, ano_estatistica);


--
-- Name: idx_ocorrencias_rubrica; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_rubrica ON public.ocorrencias_stg USING btree (rubrica);


--
-- Name: idx_ocorrencias_rubrica_data; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocorrencias_rubrica_data ON public.ocorrencias_stg USING btree (rubrica, data_ocorrencia_bo);


--
-- Name: ix_ocorrencias_stg_risk_geography; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ocorrencias_stg_risk_geography ON public.ocorrencias_stg USING gist (COALESCE(geog, (geom)::public.geography));


--
-- Name: ocorrencias_stg_geom_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ocorrencias_stg_geom_idx ON public.ocorrencias_stg USING gist (geom);


--
-- PostgreSQL database dump complete
--

\unrestrict b6eowmSwAxKiH95gn3MRUq6Tn1K5rSeaborfm2CJkDd08U88gsMGKVbXcRwiiPp

