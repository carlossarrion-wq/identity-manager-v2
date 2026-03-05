--
-- PostgreSQL database dump
--

\restrict RMPpT98QGCkNhQeU7XGgfMpgKB3BrsK8Q7U7fIfj8D6QJKomAwtmu7HqsKOQNME

-- Dumped from database version 15.16
-- Dumped by pg_dump version 15.17 (Homebrew)

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

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: administrative_block_user(character varying, character varying, timestamp without time zone, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.administrative_block_user(p_cognito_user_id character varying, p_admin_user_id character varying, p_block_until timestamp without time zone, p_reason text DEFAULT NULL::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF p_block_until <= CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Block until date must be in the future';
    END IF;
    
    -- Bloquear usuario hasta la fecha especificada
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET is_blocked = true,
        blocked_at = CURRENT_TIMESTAMP,
        blocked_until = p_block_until,
        administrative_safe = false,
        administrative_safe_set_by = p_admin_user_id,
        administrative_safe_set_at = CURRENT_TIMESTAMP,
        administrative_safe_reason = p_reason,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    -- Registrar en historial
    INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
        cognito_user_id,
        cognito_email,
        block_date,
        blocked_at,
        requests_count,
        daily_limit,
        unblocked_by,
        unblock_reason
    )
    SELECT 
        cognito_user_id,
        cognito_email,
        CURRENT_DATE,
        CURRENT_TIMESTAMP,
        requests_today,
        COALESCE(daily_request_limit, 1000),
        p_admin_user_id,
        p_reason
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN true;
END;
$$;


--
-- Name: FUNCTION administrative_block_user(p_cognito_user_id character varying, p_admin_user_id character varying, p_block_until timestamp without time zone, p_reason text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.administrative_block_user(p_cognito_user_id character varying, p_admin_user_id character varying, p_block_until timestamp without time zone, p_reason text) IS 'Bloquea un usuario administrativamente hasta una fecha/hora específica. Permite bloqueos de múltiples días.';


--
-- Name: administrative_unblock_user(character varying, character varying, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.administrative_unblock_user(p_cognito_user_id character varying, p_admin_user_id character varying, p_reason text DEFAULT NULL::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_was_blocked BOOLEAN;
BEGIN
    -- Verificar si estaba bloqueado
    SELECT is_blocked INTO v_was_blocked
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    -- Activar safe mode administrativo
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET administrative_safe = true,
        administrative_safe_set_by = p_admin_user_id,
        administrative_safe_set_at = CURRENT_TIMESTAMP,
        administrative_safe_reason = p_reason,
        is_blocked = false,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    -- Actualizar historial si estaba bloqueado
    IF v_was_blocked THEN
        UPDATE "bedrock-proxy-quota-blocks-history-tbl"
        SET unblocked_at = CURRENT_TIMESTAMP,
            unblock_type = 'administrative',
            unblocked_by = p_admin_user_id,
            unblock_reason = p_reason
        WHERE cognito_user_id = p_cognito_user_id
            AND block_date = CURRENT_DATE
            AND unblocked_at IS NULL;
    END IF;
    
    RETURN true;
END;
$$;


--
-- Name: FUNCTION administrative_unblock_user(p_cognito_user_id character varying, p_admin_user_id character varying, p_reason text); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.administrative_unblock_user(p_cognito_user_id character varying, p_admin_user_id character varying, p_reason text) IS 'Desbloquea un usuario administrativamente. El flag administrative_safe se resetea automáticamente a medianoche.';


--
-- Name: archive_old_usage_data(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.archive_old_usage_data(p_days_to_keep integer DEFAULT 365) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_deleted_count INTEGER;
    v_cutoff_date TIMESTAMP;
BEGIN
    v_cutoff_date := CURRENT_TIMESTAMP - (p_days_to_keep || ' days')::INTERVAL;
    
    -- Opción 1: Eliminar datos antiguos
    -- DELETE FROM "bedrock-proxy-usage-tracking-tbl"
    -- WHERE request_timestamp < v_cutoff_date;
    
    -- Opción 2: Mover a tabla de archivo (crear tabla de archivo primero)
    -- INSERT INTO "bedrock-proxy-usage-tracking-archive-tbl"
    -- SELECT * FROM "bedrock-proxy-usage-tracking-tbl"
    -- WHERE request_timestamp < v_cutoff_date;
    
    -- DELETE FROM "bedrock-proxy-usage-tracking-tbl"
    -- WHERE request_timestamp < v_cutoff_date;
    
    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    
    RETURN v_deleted_count;
END;
$$;


--
-- Name: FUNCTION archive_old_usage_data(p_days_to_keep integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.archive_old_usage_data(p_days_to_keep integer) IS 'Archiva o elimina datos de uso más antiguos que el número de días especificado';


--
-- Name: calculate_usage_cost(integer, integer, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_usage_cost(p_tokens_input integer, p_tokens_output integer, p_model_provider character varying) RETURNS numeric
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
    v_cost DECIMAL(10, 6);
    v_input_cost_per_1k DECIMAL(10, 6);
    v_output_cost_per_1k DECIMAL(10, 6);
BEGIN
    -- Precios aproximados por 1K tokens (actualizar según pricing real)
    CASE p_model_provider
        WHEN 'anthropic' THEN
            v_input_cost_per_1k := 0.003;
            v_output_cost_per_1k := 0.015;
        WHEN 'amazon' THEN
            v_input_cost_per_1k := 0.0008;
            v_output_cost_per_1k := 0.0024;
        WHEN 'meta' THEN
            v_input_cost_per_1k := 0.0002;
            v_output_cost_per_1k := 0.0002;
        ELSE
            v_input_cost_per_1k := 0.001;
            v_output_cost_per_1k := 0.003;
    END CASE;
    
    v_cost := (p_tokens_input::DECIMAL / 1000 * v_input_cost_per_1k) + 
              (p_tokens_output::DECIMAL / 1000 * v_output_cost_per_1k);
    
    RETURN v_cost;
END;
$$;


--
-- Name: FUNCTION calculate_usage_cost(p_tokens_input integer, p_tokens_output integer, p_model_provider character varying); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.calculate_usage_cost(p_tokens_input integer, p_tokens_output integer, p_model_provider character varying) IS 'Calcula el costo estimado basado en tokens y proveedor del modelo';


--
-- Name: check_and_update_quota(character varying, character varying, character varying, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.check_and_update_quota(p_cognito_user_id character varying, p_cognito_email character varying, p_team character varying DEFAULT NULL::character varying, p_person character varying DEFAULT NULL::character varying) RETURNS TABLE(allowed boolean, requests_today integer, daily_limit integer, is_blocked boolean, block_reason text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_quota RECORD;
    v_today DATE := CURRENT_DATE;
    v_default_limit INTEGER;
    v_effective_limit INTEGER;
BEGIN
    -- Obtener límite por defecto de configuración
    SELECT config_value::INTEGER INTO v_default_limit
    FROM "identity-manager-config-tbl"
    WHERE config_key = 'default_daily_request_limit';
    
    v_default_limit := COALESCE(v_default_limit, 1000);
    
    -- Obtener o crear registro de cuota CON daily_request_limit, team y person
    INSERT INTO "bedrock-proxy-user-quotas-tbl" (
        cognito_user_id, 
        cognito_email,
        team,
        person,
        quota_date,
        requests_today,
        daily_request_limit
    )
    VALUES (
        p_cognito_user_id, 
        p_cognito_email,
        p_team,
        p_person,
        v_today, 
        0,
        v_default_limit
    )
    ON CONFLICT (cognito_user_id) DO UPDATE
    SET daily_request_limit = COALESCE(
            "bedrock-proxy-user-quotas-tbl".daily_request_limit,
            v_default_limit
        ),
        team = COALESCE(EXCLUDED.team, "bedrock-proxy-user-quotas-tbl".team),
        person = COALESCE(EXCLUDED.person, "bedrock-proxy-user-quotas-tbl".person),
        updated_at = CURRENT_TIMESTAMP;
    
    -- Obtener estado actual
    SELECT * INTO v_quota
    FROM "bedrock-proxy-user-quotas-tbl"
    WHERE cognito_user_id = p_cognito_user_id
    FOR UPDATE;
    
    v_effective_limit := v_quota.daily_request_limit;
    
    -- Verificar si el bloqueo ha expirado
    IF v_quota.is_blocked AND v_quota.blocked_until IS NOT NULL 
       AND v_quota.blocked_until <= CURRENT_TIMESTAMP THEN
        UPDATE "bedrock-proxy-quota-blocks-history-tbl"
        SET unblocked_at = CURRENT_TIMESTAMP,
            unblock_type = 'automatic'
        WHERE cognito_user_id = p_cognito_user_id
            AND unblocked_at IS NULL;
        
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = false,
            blocked_at = NULL,
            blocked_until = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.is_blocked := false;
    END IF;
    
    -- Reset si es un nuevo día
    IF v_quota.quota_date < v_today THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET quota_date = v_today,
            requests_today = 0,
            administrative_safe = false,
            administrative_safe_set_by = NULL,
            administrative_safe_set_at = NULL,
            administrative_safe_reason = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        v_quota.quota_date := v_today;
        v_quota.requests_today := 0;
        v_quota.administrative_safe := false;
    END IF;
    
    -- Verificar si está bloqueado
    IF v_quota.is_blocked AND NOT v_quota.administrative_safe THEN
        RETURN QUERY SELECT 
            false,
            v_quota.requests_today,
            v_effective_limit,
            true,
            format('Daily quota exceeded. Blocked until %s', 
                   to_char(v_quota.blocked_until, 'YYYY-MM-DD HH24:MI:SS'))::TEXT;
        RETURN;
    END IF;
    
    -- Verificar si alcanzará el límite
    IF v_quota.requests_today >= v_effective_limit AND NOT v_quota.administrative_safe THEN
        UPDATE "bedrock-proxy-user-quotas-tbl"
        SET is_blocked = true,
            blocked_at = CURRENT_TIMESTAMP,
            blocked_until = (CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE cognito_user_id = p_cognito_user_id;
        
        INSERT INTO "bedrock-proxy-quota-blocks-history-tbl" (
            cognito_user_id,
            cognito_email,
            team,
            person,
            block_date,
            blocked_at,
            requests_count,
            daily_limit
        ) VALUES (
            p_cognito_user_id,
            p_cognito_email,
            p_team,
            p_person,
            v_today,
            CURRENT_TIMESTAMP,
            v_quota.requests_today,
            v_effective_limit
        );
        
        RETURN QUERY SELECT 
            false,
            v_quota.requests_today,
            v_effective_limit,
            true,
            format('Daily quota limit reached. User blocked until %s', 
                   to_char((CURRENT_DATE + INTERVAL '1 day')::TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS'))::TEXT;
        RETURN;
    END IF;
    
    -- Incrementar contador
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET requests_today = "bedrock-proxy-user-quotas-tbl".requests_today + 1,
        last_request_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    RETURN QUERY SELECT 
        true,
        v_quota.requests_today + 1,
        v_effective_limit,
        false,
        NULL::TEXT;
END;
$$;


--
-- Name: FUNCTION check_and_update_quota(p_cognito_user_id character varying, p_cognito_email character varying, p_team character varying, p_person character varying); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.check_and_update_quota(p_cognito_user_id character varying, p_cognito_email character varying, p_team character varying, p_person character varying) IS 'Check and update user quota with team and person information from JWT token';


--
-- Name: get_usage_stats(timestamp without time zone, timestamp without time zone, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_usage_stats(p_start_date timestamp without time zone, p_end_date timestamp without time zone, p_user_id character varying DEFAULT NULL::character varying) RETURNS TABLE(total_requests bigint, successful_requests bigint, failed_requests bigint, total_tokens_input bigint, total_tokens_output bigint, total_cost_usd numeric, avg_processing_time_ms numeric, unique_users bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT,
        COUNT(CASE WHEN response_status = 'success' THEN 1 END)::BIGINT,
        COUNT(CASE WHEN response_status != 'success' THEN 1 END)::BIGINT,
        COALESCE(SUM(tokens_input), 0)::BIGINT,
        COALESCE(SUM(tokens_output), 0)::BIGINT,
        COALESCE(SUM(cost_usd), 0)::DECIMAL(10, 2),
        COALESCE(AVG(processing_time_ms), 0)::DECIMAL(10, 2),
        COUNT(DISTINCT cognito_user_id)::BIGINT
    FROM "bedrock-proxy-usage-tracking-tbl"
    WHERE request_timestamp BETWEEN p_start_date AND p_end_date
        AND (p_user_id IS NULL OR cognito_user_id = p_user_id);
END;
$$;


--
-- Name: FUNCTION get_usage_stats(p_start_date timestamp without time zone, p_end_date timestamp without time zone, p_user_id character varying); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_usage_stats(p_start_date timestamp without time zone, p_end_date timestamp without time zone, p_user_id character varying) IS 'Obtiene estadísticas de uso para un período específico y opcionalmente para un usuario';


--
-- Name: get_user_quota_status(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_user_quota_status(p_cognito_user_id character varying) RETURNS TABLE(cognito_user_id character varying, cognito_email character varying, daily_limit integer, requests_today integer, remaining_requests integer, usage_percentage numeric, is_blocked boolean, blocked_at timestamp without time zone, administrative_safe boolean, last_request_at timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_default_limit INTEGER;
BEGIN
    RETURN QUERY
    SELECT 
        q.cognito_user_id,
        q.cognito_email,
        COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 
            1000) as daily_limit,
        q.requests_today,
        COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 
            1000) - q.requests_today as remaining_requests,
        ROUND(100.0 * q.requests_today / COALESCE(q.daily_request_limit, 
            (SELECT config_value::INTEGER FROM "identity-manager-config-tbl" 
             WHERE config_key = 'default_daily_request_limit'), 
            1000), 2) as usage_percentage,
        q.is_blocked,
        q.blocked_at,
        q.administrative_safe,
        q.last_request_at
    FROM "bedrock-proxy-user-quotas-tbl" q
    WHERE q.cognito_user_id = p_cognito_user_id;
END;
$$;


--
-- Name: FUNCTION get_user_quota_status(p_cognito_user_id character varying); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.get_user_quota_status(p_cognito_user_id character varying) IS 'Obtiene el estado actual de cuota de un usuario';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_user_daily_limit(character varying, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_user_daily_limit(p_cognito_user_id character varying, p_new_limit integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF p_new_limit < 0 THEN
        RAISE EXCEPTION 'Daily limit must be >= 0';
    END IF;
    
    UPDATE "bedrock-proxy-user-quotas-tbl"
    SET daily_request_limit = p_new_limit,
        updated_at = CURRENT_TIMESTAMP
    WHERE cognito_user_id = p_cognito_user_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User % not found', p_cognito_user_id;
    END IF;
    
    RETURN true;
END;
$$;


--
-- Name: FUNCTION update_user_daily_limit(p_cognito_user_id character varying, p_new_limit integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.update_user_daily_limit(p_cognito_user_id character varying, p_new_limit integer) IS 'Actualiza el límite diario de peticiones para un usuario específico';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bedrock-proxy-quota-blocks-history-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."bedrock-proxy-quota-blocks-history-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255) NOT NULL,
    cognito_email character varying(255) NOT NULL,
    block_date date NOT NULL,
    blocked_at timestamp without time zone NOT NULL,
    unblocked_at timestamp without time zone,
    unblock_type character varying(20),
    requests_count integer NOT NULL,
    daily_limit integer NOT NULL,
    unblocked_by character varying(255),
    unblock_reason text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    team character varying(100),
    person character varying(255)
);


--
-- Name: TABLE "bedrock-proxy-quota-blocks-history-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."bedrock-proxy-quota-blocks-history-tbl" IS 'Historial de bloqueos y desbloqueos de usuarios por cuota';


--
-- Name: COLUMN "bedrock-proxy-quota-blocks-history-tbl".team; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-quota-blocks-history-tbl".team IS 'Team name from JWT token (e.g., lcs-sdlc-gen-group)';


--
-- Name: COLUMN "bedrock-proxy-quota-blocks-history-tbl".person; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-quota-blocks-history-tbl".person IS 'Person name from JWT token (e.g., Carlos Sarrión)';


--
-- Name: bedrock-proxy-usage-tracking-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."bedrock-proxy-usage-tracking-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255) NOT NULL,
    cognito_email character varying(255) NOT NULL,
    request_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    model_id character varying(255) NOT NULL,
    source_ip character varying(45),
    user_agent text,
    aws_region character varying(50),
    tokens_input integer,
    tokens_output integer,
    tokens_cache_read integer DEFAULT 0,
    tokens_cache_creation integer DEFAULT 0,
    cost_usd numeric(10,6),
    processing_time_ms integer,
    response_status character varying(20) NOT NULL,
    error_message text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    team character varying(100),
    person character varying(255)
);


--
-- Name: TABLE "bedrock-proxy-usage-tracking-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."bedrock-proxy-usage-tracking-tbl" IS 'Registro de uso de API y modelos Bedrock con métricas de costos y rendimiento';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".id IS 'UUID único del registro de uso';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".cognito_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".cognito_user_id IS 'ID del usuario de Cognito que realizó la petición';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".cognito_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".cognito_email IS 'Email del usuario de Cognito';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".request_timestamp; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".request_timestamp IS 'Timestamp de cuando se realizó la petición';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".model_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".model_id IS 'Model identifier - can be a UUID or an ARN (e.g., arn:aws:bedrock:region:account:application-inference-profile/id)';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".source_ip; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".source_ip IS 'Dirección IP de origen de la petición';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".user_agent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".user_agent IS 'User agent del cliente que realizó la petición';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".aws_region; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".aws_region IS 'Región de AWS donde se procesó la petición';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".tokens_input; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".tokens_input IS 'Número de tokens de entrada procesados';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".tokens_output; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".tokens_output IS 'Número de tokens de salida generados';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".tokens_cache_read; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".tokens_cache_read IS 'Número de tokens leídos desde caché';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".tokens_cache_creation; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".tokens_cache_creation IS 'Número de tokens escritos en caché';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".cost_usd; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".cost_usd IS 'Coste aproximado de la petición en USD';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".processing_time_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".processing_time_ms IS 'Tiempo de procesamiento en milisegundos';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".response_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".response_status IS 'Estado de la respuesta (success, error, timeout, etc.)';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".error_message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".error_message IS 'Mensaje de error si la petición falló';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".created_at IS 'Timestamp de creación del registro';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".team; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".team IS 'Team name from JWT token (e.g., lcs-sdlc-gen-group)';


--
-- Name: COLUMN "bedrock-proxy-usage-tracking-tbl".person; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-usage-tracking-tbl".person IS 'Person name from JWT token (e.g., Carlos Sarrión)';


--
-- Name: bedrock-proxy-user-quotas-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."bedrock-proxy-user-quotas-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255) NOT NULL,
    cognito_email character varying(255) NOT NULL,
    daily_request_limit integer,
    quota_date date DEFAULT CURRENT_DATE NOT NULL,
    requests_today integer DEFAULT 0 NOT NULL,
    is_blocked boolean DEFAULT false NOT NULL,
    blocked_at timestamp without time zone,
    blocked_until timestamp without time zone,
    administrative_safe boolean DEFAULT false NOT NULL,
    administrative_safe_set_by character varying(255),
    administrative_safe_set_at timestamp without time zone,
    administrative_safe_reason text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_request_at timestamp without time zone,
    team character varying(100),
    person character varying(255)
);


--
-- Name: TABLE "bedrock-proxy-user-quotas-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."bedrock-proxy-user-quotas-tbl" IS 'Control de cuotas diarias por usuario con bloqueo automático';


--
-- Name: COLUMN "bedrock-proxy-user-quotas-tbl".daily_request_limit; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-user-quotas-tbl".daily_request_limit IS 'Límite diario específico del usuario. NULL = usar default_daily_request_limit de config';


--
-- Name: COLUMN "bedrock-proxy-user-quotas-tbl".blocked_until; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-user-quotas-tbl".blocked_until IS 'Fecha/hora hasta la cual el usuario está bloqueado. NULL = no bloqueado. Permite bloqueos de múltiples días en el futuro';


--
-- Name: COLUMN "bedrock-proxy-user-quotas-tbl".administrative_safe; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-user-quotas-tbl".administrative_safe IS 'Flag administrativo que permite al usuario continuar hasta medianoche. Se resetea automáticamente cada día';


--
-- Name: COLUMN "bedrock-proxy-user-quotas-tbl".team; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-user-quotas-tbl".team IS 'Team name from JWT token (e.g., lcs-sdlc-gen-group)';


--
-- Name: COLUMN "bedrock-proxy-user-quotas-tbl".person; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."bedrock-proxy-user-quotas-tbl".person IS 'Person name from JWT token (e.g., Carlos Sarrión)';


--
-- Name: identity-manager-app-permissions-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-app-permissions-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255) NOT NULL,
    cognito_email character varying(255) NOT NULL,
    application_id uuid NOT NULL,
    permission_type_id uuid NOT NULL,
    granted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE "identity-manager-app-permissions-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-app-permissions-tbl" IS 'Permisos de usuarios sobre aplicaciones completas';


--
-- Name: COLUMN "identity-manager-app-permissions-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-app-permissions-tbl".id IS 'UUID único del permiso';


--
-- Name: identity-manager-applications-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-applications-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    display_order integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-applications-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-applications-tbl" IS 'Aplicaciones disponibles en el sistema (ej: cline, kb-agent)';


--
-- Name: COLUMN "identity-manager-applications-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-applications-tbl".id IS 'UUID único de la aplicación';


--
-- Name: identity-manager-audit-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-audit-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255),
    cognito_email character varying(255),
    performed_by_cognito_user_id character varying(255),
    performed_by_email character varying(255),
    operation_type character varying(100) NOT NULL,
    resource_type character varying(50) NOT NULL,
    resource_id uuid,
    previous_value jsonb,
    new_value jsonb,
    ip_address character varying(45),
    user_agent text,
    operation_timestamp timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-audit-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-audit-tbl" IS 'Registro de auditoría de todas las operaciones del sistema';


--
-- Name: COLUMN "identity-manager-audit-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-audit-tbl".id IS 'UUID único del registro de auditoría';


--
-- Name: COLUMN "identity-manager-audit-tbl".resource_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-audit-tbl".resource_id IS 'UUID del recurso afectado';


--
-- Name: identity-manager-config-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-config-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    config_key character varying(100) NOT NULL,
    config_value text NOT NULL,
    description text,
    is_sensitive boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-config-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-config-tbl" IS 'Parámetros de configuración de la aplicación';


--
-- Name: COLUMN "identity-manager-config-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-config-tbl".id IS 'UUID único de la configuración';


--
-- Name: identity-manager-models-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-models-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    model_id character varying(255) NOT NULL,
    model_name character varying(255) NOT NULL,
    model_arn character varying(500),
    provider character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-models-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-models-tbl" IS 'Catálogo de modelos LLM disponibles en AWS Bedrock';


--
-- Name: COLUMN "identity-manager-models-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-models-tbl".id IS 'UUID único del modelo';


--
-- Name: COLUMN "identity-manager-models-tbl".model_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-models-tbl".model_id IS 'Identificador del modelo en Bedrock (ej: anthropic.claude-3-5-sonnet-20241022-v2:0)';


--
-- Name: identity-manager-module-permissions-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-module-permissions-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255) NOT NULL,
    cognito_email character varying(255) NOT NULL,
    application_module_id uuid NOT NULL,
    permission_type_id uuid NOT NULL,
    granted_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone,
    is_active boolean DEFAULT true NOT NULL
);


--
-- Name: TABLE "identity-manager-module-permissions-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-module-permissions-tbl" IS 'Permisos de usuarios sobre módulos específicos de aplicaciones';


--
-- Name: COLUMN "identity-manager-module-permissions-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-module-permissions-tbl".id IS 'UUID único del permiso';


--
-- Name: identity-manager-modules-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-modules-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    application_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    display_order integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-modules-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-modules-tbl" IS 'Módulos específicos de cada aplicación';


--
-- Name: COLUMN "identity-manager-modules-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-modules-tbl".id IS 'UUID único del módulo';


--
-- Name: identity-manager-permission-types-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-permission-types-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(50) NOT NULL,
    description text,
    level integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-permission-types-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-permission-types-tbl" IS 'Catálogo de tipos de permisos (Read-only, Write, Admin, etc.)';


--
-- Name: COLUMN "identity-manager-permission-types-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-permission-types-tbl".id IS 'UUID único del tipo de permiso';


--
-- Name: COLUMN "identity-manager-permission-types-tbl".level; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-permission-types-tbl".level IS 'Nivel jerárquico del permiso (1=menor, 100=mayor)';


--
-- Name: identity-manager-profiles-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-profiles-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    profile_name character varying(100) NOT NULL,
    cognito_group_name character varying(100) NOT NULL,
    application_id uuid,
    model_id uuid NOT NULL,
    model_arn text NOT NULL,
    description text,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE "identity-manager-profiles-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-profiles-tbl" IS 'Perfiles que asocian un grupo de Cognito, aplicación y modelo LLM';


--
-- Name: COLUMN "identity-manager-profiles-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-profiles-tbl".id IS 'UUID único del perfil';


--
-- Name: COLUMN "identity-manager-profiles-tbl".cognito_group_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-profiles-tbl".cognito_group_name IS 'Nombre del grupo en Cognito (ej: tcs-bi-dwh-group)';


--
-- Name: identity-manager-tokens-tbl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."identity-manager-tokens-tbl" (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cognito_user_id character varying(255) NOT NULL,
    cognito_email character varying(255) NOT NULL,
    jti character varying(255) NOT NULL,
    token_hash text NOT NULL,
    application_profile_id uuid NOT NULL,
    issued_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    last_used_at timestamp without time zone,
    is_revoked boolean DEFAULT false NOT NULL,
    revoked_at timestamp without time zone,
    revocation_reason text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    regenerated_at timestamp without time zone,
    regenerated_to_jti uuid,
    regenerated_from_jti uuid,
    regeneration_reason character varying(100),
    regeneration_client_ip character varying(45),
    regeneration_user_agent text,
    regeneration_email_sent boolean DEFAULT false
);


--
-- Name: TABLE "identity-manager-tokens-tbl"; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public."identity-manager-tokens-tbl" IS 'Tokens JWT emitidos a usuarios para acceso al proxy de Bedrock';


--
-- Name: COLUMN "identity-manager-tokens-tbl".id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".id IS 'UUID único del token';


--
-- Name: COLUMN "identity-manager-tokens-tbl".jti; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".jti IS 'JWT ID único del token';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regenerated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regenerated_at IS 'Timestamp when this token was regenerated (replaced by a new one)';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regenerated_to_jti; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regenerated_to_jti IS 'JTI of the new token that replaced this one (if this token was regenerated)';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regenerated_from_jti; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regenerated_from_jti IS 'JTI of the old token that this token replaced (if this token is a regeneration)';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regeneration_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regeneration_reason IS 'Reason for regeneration (e.g., auto_regeneration, manual)';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regeneration_client_ip; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regeneration_client_ip IS 'IP address of the client that triggered regeneration';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regeneration_user_agent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regeneration_user_agent IS 'User agent of the client that triggered regeneration';


--
-- Name: COLUMN "identity-manager-tokens-tbl".regeneration_email_sent; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public."identity-manager-tokens-tbl".regeneration_email_sent IS 'Whether notification email was sent successfully';


--
-- Name: v_active_tokens; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_active_tokens AS
 SELECT t.id AS token_id,
    t.jti,
    t.cognito_user_id,
    t.cognito_email,
    t.issued_at,
    t.expires_at,
    t.last_used_at,
    ap.profile_name,
    ap.cognito_group_name,
    a.name AS application_name,
    m.model_name,
    m.model_id,
    ap.model_arn
   FROM (((public."identity-manager-tokens-tbl" t
     JOIN public."identity-manager-profiles-tbl" ap ON ((t.application_profile_id = ap.id)))
     LEFT JOIN public."identity-manager-applications-tbl" a ON ((ap.application_id = a.id)))
     JOIN public."identity-manager-models-tbl" m ON ((ap.model_id = m.id)))
  WHERE ((t.is_revoked = false) AND (t.expires_at > CURRENT_TIMESTAMP));


--
-- Name: v_application_profiles; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_application_profiles AS
 SELECT ap.id,
    ap.profile_name,
    ap.cognito_group_name,
    a.name AS application_name,
    a.id AS application_id,
    m.model_name,
    m.model_id,
    m.provider,
    ap.model_arn,
    ap.is_active,
    ap.created_at,
    ap.updated_at
   FROM ((public."identity-manager-profiles-tbl" ap
     LEFT JOIN public."identity-manager-applications-tbl" a ON ((ap.application_id = a.id)))
     JOIN public."identity-manager-models-tbl" m ON ((ap.model_id = m.id)));


--
-- Name: v_blocked_users; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_blocked_users AS
 SELECT q.cognito_user_id,
    q.cognito_email,
    q.requests_today,
    COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000) AS daily_request_limit,
    q.blocked_at,
    q.blocked_until,
    q.administrative_safe,
    (EXTRACT(epoch FROM (CURRENT_TIMESTAMP - (q.blocked_at)::timestamp with time zone)) / (3600)::numeric) AS hours_blocked,
    (EXTRACT(epoch FROM ((q.blocked_until)::timestamp with time zone - CURRENT_TIMESTAMP)) / (3600)::numeric) AS hours_remaining
   FROM public."bedrock-proxy-user-quotas-tbl" q
  WHERE (q.is_blocked = true);


--
-- Name: VIEW v_blocked_users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_blocked_users IS 'Lista de usuarios actualmente bloqueados por cuota';


--
-- Name: v_quota_status; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_quota_status AS
 SELECT q.cognito_user_id,
    q.cognito_email,
    COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000) AS daily_request_limit,
    q.requests_today,
    (COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000) - q.requests_today) AS remaining_requests,
    round(((100.0 * (q.requests_today)::numeric) / (COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000))::numeric), 2) AS usage_percentage,
    q.is_blocked,
    q.blocked_at,
    q.blocked_until,
    q.administrative_safe,
    q.administrative_safe_set_by,
    q.administrative_safe_reason,
    q.last_request_at,
    q.quota_date
   FROM public."bedrock-proxy-user-quotas-tbl" q;


--
-- Name: VIEW v_quota_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_quota_status IS 'Vista consolidada del estado de cuotas de todos los usuarios';


--
-- Name: v_recent_errors; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_recent_errors AS
 SELECT "bedrock-proxy-usage-tracking-tbl".id,
    "bedrock-proxy-usage-tracking-tbl".cognito_user_id,
    "bedrock-proxy-usage-tracking-tbl".cognito_email,
    "bedrock-proxy-usage-tracking-tbl".person,
    "bedrock-proxy-usage-tracking-tbl".team,
    "bedrock-proxy-usage-tracking-tbl".request_timestamp,
    "bedrock-proxy-usage-tracking-tbl".model_id,
    "bedrock-proxy-usage-tracking-tbl".response_status,
    "bedrock-proxy-usage-tracking-tbl".error_message,
    "bedrock-proxy-usage-tracking-tbl".created_at
   FROM public."bedrock-proxy-usage-tracking-tbl"
  WHERE (("bedrock-proxy-usage-tracking-tbl".response_status)::text <> 'success'::text)
  ORDER BY "bedrock-proxy-usage-tracking-tbl".request_timestamp DESC
 LIMIT 100;


--
-- Name: v_top_users_by_cost; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_top_users_by_cost AS
 SELECT u.cognito_user_id,
    u.cognito_email,
    count(*) AS total_requests,
    sum(u.cost_usd) AS total_cost_usd,
    avg(u.cost_usd) AS avg_cost_per_request,
    sum((u.tokens_input + u.tokens_output)) AS total_tokens
   FROM public."bedrock-proxy-usage-tracking-tbl" u
  GROUP BY u.cognito_user_id, u.cognito_email
  ORDER BY (sum(u.cost_usd)) DESC;


--
-- Name: VIEW v_top_users_by_cost; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_top_users_by_cost IS 'Top usuarios ordenados por costo total';


--
-- Name: v_usage_by_model; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_usage_by_model AS
 SELECT "bedrock-proxy-usage-tracking-tbl".model_id,
    count(*) AS request_count,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_input) AS total_tokens_input,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_output) AS total_tokens_output,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_cache_read) AS total_tokens_cache_read,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_cache_creation) AS total_tokens_cache_creation,
    sum("bedrock-proxy-usage-tracking-tbl".cost_usd) AS total_cost_usd,
    avg("bedrock-proxy-usage-tracking-tbl".processing_time_ms) AS avg_processing_time_ms,
    min("bedrock-proxy-usage-tracking-tbl".request_timestamp) AS first_request,
    max("bedrock-proxy-usage-tracking-tbl".request_timestamp) AS last_request
   FROM public."bedrock-proxy-usage-tracking-tbl"
  GROUP BY "bedrock-proxy-usage-tracking-tbl".model_id
  ORDER BY (count(*)) DESC;


--
-- Name: v_usage_by_person; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_usage_by_person AS
 SELECT "bedrock-proxy-usage-tracking-tbl".person,
    "bedrock-proxy-usage-tracking-tbl".cognito_email,
    "bedrock-proxy-usage-tracking-tbl".team,
    count(*) AS request_count,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_input) AS total_tokens_input,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_output) AS total_tokens_output,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_cache_read) AS total_tokens_cache_read,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_cache_creation) AS total_tokens_cache_creation,
    sum("bedrock-proxy-usage-tracking-tbl".cost_usd) AS total_cost_usd,
    avg("bedrock-proxy-usage-tracking-tbl".processing_time_ms) AS avg_processing_time_ms,
    min("bedrock-proxy-usage-tracking-tbl".request_timestamp) AS first_request,
    max("bedrock-proxy-usage-tracking-tbl".request_timestamp) AS last_request
   FROM public."bedrock-proxy-usage-tracking-tbl"
  WHERE ("bedrock-proxy-usage-tracking-tbl".person IS NOT NULL)
  GROUP BY "bedrock-proxy-usage-tracking-tbl".person, "bedrock-proxy-usage-tracking-tbl".cognito_email, "bedrock-proxy-usage-tracking-tbl".team
  ORDER BY (count(*)) DESC;


--
-- Name: VIEW v_usage_by_person; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_usage_by_person IS 'Aggregated usage statistics by person';


--
-- Name: v_usage_by_team; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_usage_by_team AS
 SELECT "bedrock-proxy-usage-tracking-tbl".team,
    count(*) AS request_count,
    count(DISTINCT "bedrock-proxy-usage-tracking-tbl".cognito_user_id) AS unique_users,
    count(DISTINCT "bedrock-proxy-usage-tracking-tbl".person) AS unique_persons,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_input) AS total_tokens_input,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_output) AS total_tokens_output,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_cache_read) AS total_tokens_cache_read,
    sum("bedrock-proxy-usage-tracking-tbl".tokens_cache_creation) AS total_tokens_cache_creation,
    sum("bedrock-proxy-usage-tracking-tbl".cost_usd) AS total_cost_usd,
    avg("bedrock-proxy-usage-tracking-tbl".processing_time_ms) AS avg_processing_time_ms,
    min("bedrock-proxy-usage-tracking-tbl".request_timestamp) AS first_request,
    max("bedrock-proxy-usage-tracking-tbl".request_timestamp) AS last_request
   FROM public."bedrock-proxy-usage-tracking-tbl"
  WHERE ("bedrock-proxy-usage-tracking-tbl".team IS NOT NULL)
  GROUP BY "bedrock-proxy-usage-tracking-tbl".team
  ORDER BY (count(*)) DESC;


--
-- Name: VIEW v_usage_by_team; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_usage_by_team IS 'Aggregated usage statistics by team including person count';


--
-- Name: v_usage_daily; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_usage_daily AS
 SELECT date(u.request_timestamp) AS usage_date,
    count(*) AS total_requests,
    count(DISTINCT u.cognito_user_id) AS unique_users,
    count(
        CASE
            WHEN ((u.response_status)::text = 'success'::text) THEN 1
            ELSE NULL::integer
        END) AS successful_requests,
    count(
        CASE
            WHEN ((u.response_status)::text <> 'success'::text) THEN 1
            ELSE NULL::integer
        END) AS failed_requests,
    sum(u.tokens_input) AS total_tokens_input,
    sum(u.tokens_output) AS total_tokens_output,
    sum(u.tokens_cache_read) AS total_tokens_cache_read,
    sum(u.tokens_cache_creation) AS total_tokens_cache_creation,
    sum(u.cost_usd) AS total_cost_usd,
    avg(u.processing_time_ms) AS avg_processing_time_ms
   FROM public."bedrock-proxy-usage-tracking-tbl" u
  GROUP BY (date(u.request_timestamp))
  ORDER BY (date(u.request_timestamp)) DESC;


--
-- Name: VIEW v_usage_daily; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_usage_daily IS 'Resumen agregado de uso por día';


--
-- Name: v_usage_detailed; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_usage_detailed AS
 SELECT "bedrock-proxy-usage-tracking-tbl".id,
    "bedrock-proxy-usage-tracking-tbl".cognito_user_id,
    "bedrock-proxy-usage-tracking-tbl".cognito_email,
    "bedrock-proxy-usage-tracking-tbl".person,
    "bedrock-proxy-usage-tracking-tbl".team,
    "bedrock-proxy-usage-tracking-tbl".request_timestamp,
    "bedrock-proxy-usage-tracking-tbl".model_id,
    "bedrock-proxy-usage-tracking-tbl".source_ip,
    "bedrock-proxy-usage-tracking-tbl".user_agent,
    "bedrock-proxy-usage-tracking-tbl".aws_region,
    "bedrock-proxy-usage-tracking-tbl".tokens_input,
    "bedrock-proxy-usage-tracking-tbl".tokens_output,
    "bedrock-proxy-usage-tracking-tbl".tokens_cache_read,
    "bedrock-proxy-usage-tracking-tbl".tokens_cache_creation,
    "bedrock-proxy-usage-tracking-tbl".cost_usd,
    "bedrock-proxy-usage-tracking-tbl".processing_time_ms,
    "bedrock-proxy-usage-tracking-tbl".response_status,
    "bedrock-proxy-usage-tracking-tbl".error_message,
    "bedrock-proxy-usage-tracking-tbl".created_at
   FROM public."bedrock-proxy-usage-tracking-tbl"
  ORDER BY "bedrock-proxy-usage-tracking-tbl".request_timestamp DESC;


--
-- Name: v_user_permissions; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_user_permissions AS
 SELECT uap.cognito_user_id,
    uap.cognito_email,
    'application'::text AS permission_scope,
    a.name AS resource_name,
    a.id AS resource_id,
    NULL::uuid AS parent_application_id,
    pt.name AS permission_type,
    pt.level AS permission_level,
    uap.is_active,
    uap.granted_at,
    uap.expires_at
   FROM ((public."identity-manager-app-permissions-tbl" uap
     JOIN public."identity-manager-applications-tbl" a ON ((uap.application_id = a.id)))
     JOIN public."identity-manager-permission-types-tbl" pt ON ((uap.permission_type_id = pt.id)))
UNION ALL
 SELECT ump.cognito_user_id,
    ump.cognito_email,
    'module'::text AS permission_scope,
    am.name AS resource_name,
    am.id AS resource_id,
    am.application_id AS parent_application_id,
    pt.name AS permission_type,
    pt.level AS permission_level,
    ump.is_active,
    ump.granted_at,
    ump.expires_at
   FROM ((public."identity-manager-module-permissions-tbl" ump
     JOIN public."identity-manager-modules-tbl" am ON ((ump.application_module_id = am.id)))
     JOIN public."identity-manager-permission-types-tbl" pt ON ((ump.permission_type_id = pt.id)));


--
-- Name: v_users_near_limit; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_users_near_limit AS
 SELECT q.cognito_user_id,
    q.cognito_email,
    q.requests_today,
    COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000) AS daily_request_limit,
    (COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000) - q.requests_today) AS remaining,
    round(((100.0 * (q.requests_today)::numeric) / (COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000))::numeric), 2) AS usage_pct
   FROM public."bedrock-proxy-user-quotas-tbl" q
  WHERE (((q.requests_today)::numeric >= ((COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000))::numeric * 0.8)) AND (q.is_blocked = false) AND (q.quota_date = CURRENT_DATE))
  ORDER BY (round(((100.0 * (q.requests_today)::numeric) / (COALESCE(q.daily_request_limit, ( SELECT ("identity-manager-config-tbl".config_value)::integer AS config_value
           FROM public."identity-manager-config-tbl"
          WHERE (("identity-manager-config-tbl".config_key)::text = 'default_daily_request_limit'::text)), 1000))::numeric), 2)) DESC;


--
-- Name: VIEW v_users_near_limit; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON VIEW public.v_users_near_limit IS 'Usuarios que han usado más del 80% de su cuota diaria';


--
-- Name: bedrock-proxy-quota-blocks-history-tbl bedrock-proxy-quota-blocks-history-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."bedrock-proxy-quota-blocks-history-tbl"
    ADD CONSTRAINT "bedrock-proxy-quota-blocks-history-tbl_pkey" PRIMARY KEY (id);


--
-- Name: bedrock-proxy-usage-tracking-tbl bedrock-proxy-usage-tracking-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."bedrock-proxy-usage-tracking-tbl"
    ADD CONSTRAINT "bedrock-proxy-usage-tracking-tbl_pkey" PRIMARY KEY (id);


--
-- Name: bedrock-proxy-user-quotas-tbl bedrock-proxy-user-quotas-tbl_cognito_user_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."bedrock-proxy-user-quotas-tbl"
    ADD CONSTRAINT "bedrock-proxy-user-quotas-tbl_cognito_user_id_key" UNIQUE (cognito_user_id);


--
-- Name: bedrock-proxy-user-quotas-tbl bedrock-proxy-user-quotas-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."bedrock-proxy-user-quotas-tbl"
    ADD CONSTRAINT "bedrock-proxy-user-quotas-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-app-permissions-tbl identity-manager-app-permissions-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-app-permissions-tbl"
    ADD CONSTRAINT "identity-manager-app-permissions-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-applications-tbl identity-manager-applications-tbl_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-applications-tbl"
    ADD CONSTRAINT "identity-manager-applications-tbl_name_key" UNIQUE (name);


--
-- Name: identity-manager-applications-tbl identity-manager-applications-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-applications-tbl"
    ADD CONSTRAINT "identity-manager-applications-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-audit-tbl identity-manager-audit-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-audit-tbl"
    ADD CONSTRAINT "identity-manager-audit-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-config-tbl identity-manager-config-tbl_config_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-config-tbl"
    ADD CONSTRAINT "identity-manager-config-tbl_config_key_key" UNIQUE (config_key);


--
-- Name: identity-manager-config-tbl identity-manager-config-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-config-tbl"
    ADD CONSTRAINT "identity-manager-config-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-models-tbl identity-manager-models-tbl_model_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-models-tbl"
    ADD CONSTRAINT "identity-manager-models-tbl_model_id_key" UNIQUE (model_id);


--
-- Name: identity-manager-models-tbl identity-manager-models-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-models-tbl"
    ADD CONSTRAINT "identity-manager-models-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-module-permissions-tbl identity-manager-module-permissions-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-module-permissions-tbl"
    ADD CONSTRAINT "identity-manager-module-permissions-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-modules-tbl identity-manager-modules-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-modules-tbl"
    ADD CONSTRAINT "identity-manager-modules-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-permission-types-tbl identity-manager-permission-types-tbl_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-permission-types-tbl"
    ADD CONSTRAINT "identity-manager-permission-types-tbl_name_key" UNIQUE (name);


--
-- Name: identity-manager-permission-types-tbl identity-manager-permission-types-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-permission-types-tbl"
    ADD CONSTRAINT "identity-manager-permission-types-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-profiles-tbl identity-manager-profiles-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-profiles-tbl"
    ADD CONSTRAINT "identity-manager-profiles-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-tokens-tbl identity-manager-tokens-tbl_jti_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-tokens-tbl"
    ADD CONSTRAINT "identity-manager-tokens-tbl_jti_key" UNIQUE (jti);


--
-- Name: identity-manager-tokens-tbl identity-manager-tokens-tbl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-tokens-tbl"
    ADD CONSTRAINT "identity-manager-tokens-tbl_pkey" PRIMARY KEY (id);


--
-- Name: identity-manager-tokens-tbl identity-manager-tokens-tbl_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-tokens-tbl"
    ADD CONSTRAINT "identity-manager-tokens-tbl_token_hash_key" UNIQUE (token_hash);


--
-- Name: identity-manager-modules-tbl uk_application_module_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-modules-tbl"
    ADD CONSTRAINT uk_application_module_name UNIQUE (application_id, name);


--
-- Name: identity-manager-profiles-tbl uk_profile_group_app_model; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-profiles-tbl"
    ADD CONSTRAINT uk_profile_group_app_model UNIQUE (cognito_group_name, application_id, model_id);


--
-- Name: identity-manager-app-permissions-tbl uk_user_application_permission; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-app-permissions-tbl"
    ADD CONSTRAINT uk_user_application_permission UNIQUE (cognito_user_id, application_id);


--
-- Name: identity-manager-module-permissions-tbl uk_user_module_permission; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-module-permissions-tbl"
    ADD CONSTRAINT uk_user_module_permission UNIQUE (cognito_user_id, application_module_id);


--
-- Name: idx_app_perms_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_perms_user ON public."identity-manager-app-permissions-tbl" USING btree (cognito_user_id);


--
-- Name: idx_audit_performed_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_performed_by ON public."identity-manager-audit-tbl" USING btree (performed_by_cognito_user_id);


--
-- Name: idx_audit_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_resource ON public."identity-manager-audit-tbl" USING btree (resource_type, resource_id);


--
-- Name: idx_audit_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_timestamp ON public."identity-manager-audit-tbl" USING btree (operation_timestamp DESC);


--
-- Name: idx_audit_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_user ON public."identity-manager-audit-tbl" USING btree (cognito_user_id);


--
-- Name: idx_mod_perms_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mod_perms_user ON public."identity-manager-module-permissions-tbl" USING btree (cognito_user_id);


--
-- Name: idx_quota_history_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_history_date ON public."bedrock-proxy-quota-blocks-history-tbl" USING btree (block_date DESC);


--
-- Name: idx_quota_history_person; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_history_person ON public."bedrock-proxy-quota-blocks-history-tbl" USING btree (person);


--
-- Name: idx_quota_history_team; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_history_team ON public."bedrock-proxy-quota-blocks-history-tbl" USING btree (team);


--
-- Name: idx_quota_history_unblocked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_history_unblocked ON public."bedrock-proxy-quota-blocks-history-tbl" USING btree (unblocked_at) WHERE (unblocked_at IS NULL);


--
-- Name: idx_quota_history_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quota_history_user ON public."bedrock-proxy-quota-blocks-history-tbl" USING btree (cognito_user_id);


--
-- Name: idx_quotas_admin_safe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quotas_admin_safe ON public."bedrock-proxy-user-quotas-tbl" USING btree (administrative_safe) WHERE (administrative_safe = true);


--
-- Name: idx_quotas_blocked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quotas_blocked ON public."bedrock-proxy-user-quotas-tbl" USING btree (is_blocked) WHERE (is_blocked = true);


--
-- Name: idx_quotas_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quotas_date ON public."bedrock-proxy-user-quotas-tbl" USING btree (quota_date);


--
-- Name: idx_quotas_person; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quotas_person ON public."bedrock-proxy-user-quotas-tbl" USING btree (person);


--
-- Name: idx_quotas_team; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quotas_team ON public."bedrock-proxy-user-quotas-tbl" USING btree (team);


--
-- Name: idx_quotas_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_quotas_user_id ON public."bedrock-proxy-user-quotas-tbl" USING btree (cognito_user_id);


--
-- Name: idx_tokens_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_active ON public."identity-manager-tokens-tbl" USING btree (is_revoked, expires_at);


--
-- Name: idx_tokens_cognito_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_cognito_user ON public."identity-manager-tokens-tbl" USING btree (cognito_user_id);


--
-- Name: idx_tokens_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_expires ON public."identity-manager-tokens-tbl" USING btree (expires_at);


--
-- Name: idx_tokens_jti; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_jti ON public."identity-manager-tokens-tbl" USING btree (jti);


--
-- Name: idx_tokens_regenerated; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_regenerated ON public."identity-manager-tokens-tbl" USING btree (regenerated_at) WHERE (regenerated_at IS NOT NULL);


--
-- Name: INDEX idx_tokens_regenerated; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_tokens_regenerated IS 'Index for quickly finding tokens that were regenerated (old tokens)';


--
-- Name: idx_tokens_regenerated_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_regenerated_from ON public."identity-manager-tokens-tbl" USING btree (regenerated_from_jti) WHERE (regenerated_from_jti IS NOT NULL);


--
-- Name: INDEX idx_tokens_regenerated_from; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_tokens_regenerated_from IS 'Index for finding tokens that are regenerations of other tokens (new tokens)';


--
-- Name: idx_tokens_regenerated_to; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tokens_regenerated_to ON public."identity-manager-tokens-tbl" USING btree (regenerated_to_jti) WHERE (regenerated_to_jti IS NOT NULL);


--
-- Name: INDEX idx_tokens_regenerated_to; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.idx_tokens_regenerated_to IS 'Index for finding the new token that replaced an old one';


--
-- Name: idx_usage_cognito_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_cognito_email ON public."bedrock-proxy-usage-tracking-tbl" USING btree (cognito_email);


--
-- Name: idx_usage_cognito_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_cognito_user ON public."bedrock-proxy-usage-tracking-tbl" USING btree (cognito_user_id);


--
-- Name: idx_usage_errors; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_errors ON public."bedrock-proxy-usage-tracking-tbl" USING btree (response_status, request_timestamp DESC) WHERE ((response_status)::text <> 'success'::text);


--
-- Name: idx_usage_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_model ON public."bedrock-proxy-usage-tracking-tbl" USING btree (model_id);


--
-- Name: idx_usage_model_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_model_timestamp ON public."bedrock-proxy-usage-tracking-tbl" USING btree (model_id, request_timestamp DESC);


--
-- Name: idx_usage_person; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_person ON public."bedrock-proxy-usage-tracking-tbl" USING btree (person);


--
-- Name: idx_usage_request_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_request_timestamp ON public."bedrock-proxy-usage-tracking-tbl" USING btree (request_timestamp DESC);


--
-- Name: idx_usage_response_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_response_status ON public."bedrock-proxy-usage-tracking-tbl" USING btree (response_status);


--
-- Name: idx_usage_team; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_team ON public."bedrock-proxy-usage-tracking-tbl" USING btree (team);


--
-- Name: idx_usage_user_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_user_timestamp ON public."bedrock-proxy-usage-tracking-tbl" USING btree (cognito_user_id, request_timestamp DESC);


--
-- Name: identity-manager-applications-tbl trg_applications_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_applications_updated_at BEFORE UPDATE ON public."identity-manager-applications-tbl" FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: identity-manager-config-tbl trg_config_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_config_updated_at BEFORE UPDATE ON public."identity-manager-config-tbl" FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: identity-manager-models-tbl trg_models_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_models_updated_at BEFORE UPDATE ON public."identity-manager-models-tbl" FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: identity-manager-modules-tbl trg_modules_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_modules_updated_at BEFORE UPDATE ON public."identity-manager-modules-tbl" FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: identity-manager-profiles-tbl trg_profiles_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_profiles_updated_at BEFORE UPDATE ON public."identity-manager-profiles-tbl" FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: bedrock-proxy-user-quotas-tbl trg_quotas_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_quotas_updated_at BEFORE UPDATE ON public."bedrock-proxy-user-quotas-tbl" FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: identity-manager-app-permissions-tbl fk_app_perms_application; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-app-permissions-tbl"
    ADD CONSTRAINT fk_app_perms_application FOREIGN KEY (application_id) REFERENCES public."identity-manager-applications-tbl"(id) ON DELETE CASCADE;


--
-- Name: identity-manager-app-permissions-tbl fk_app_perms_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-app-permissions-tbl"
    ADD CONSTRAINT fk_app_perms_type FOREIGN KEY (permission_type_id) REFERENCES public."identity-manager-permission-types-tbl"(id) ON DELETE RESTRICT;


--
-- Name: identity-manager-module-permissions-tbl fk_mod_perms_module; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-module-permissions-tbl"
    ADD CONSTRAINT fk_mod_perms_module FOREIGN KEY (application_module_id) REFERENCES public."identity-manager-modules-tbl"(id) ON DELETE CASCADE;


--
-- Name: identity-manager-module-permissions-tbl fk_mod_perms_type; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-module-permissions-tbl"
    ADD CONSTRAINT fk_mod_perms_type FOREIGN KEY (permission_type_id) REFERENCES public."identity-manager-permission-types-tbl"(id) ON DELETE RESTRICT;


--
-- Name: identity-manager-modules-tbl fk_modules_application; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-modules-tbl"
    ADD CONSTRAINT fk_modules_application FOREIGN KEY (application_id) REFERENCES public."identity-manager-applications-tbl"(id) ON DELETE CASCADE;


--
-- Name: identity-manager-profiles-tbl fk_profiles_application; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-profiles-tbl"
    ADD CONSTRAINT fk_profiles_application FOREIGN KEY (application_id) REFERENCES public."identity-manager-applications-tbl"(id) ON DELETE SET NULL;


--
-- Name: identity-manager-profiles-tbl fk_profiles_model; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-profiles-tbl"
    ADD CONSTRAINT fk_profiles_model FOREIGN KEY (model_id) REFERENCES public."identity-manager-models-tbl"(id) ON DELETE RESTRICT;


--
-- Name: identity-manager-tokens-tbl fk_tokens_profile; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."identity-manager-tokens-tbl"
    ADD CONSTRAINT fk_tokens_profile FOREIGN KEY (application_profile_id) REFERENCES public."identity-manager-profiles-tbl"(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict RMPpT98QGCkNhQeU7XGgfMpgKB3BrsK8Q7U7fIfj8D6QJKomAwtmu7HqsKOQNME

