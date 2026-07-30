-- ============================================================
-- init_db.sql - Estrutura inicial do banco BID Hospital
-- ============================================================
-- Executado automaticamente na primeira inicialização
-- do container PostgreSQL.
-- ============================================================

-- Módulos do BID (fluxo, cirurgias, emergencia, etc)
CREATE TABLE IF NOT EXISTS bid_modulo (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(50)  NOT NULL UNIQUE,  -- 'fluxo', 'cirurgia', 'emergencia'
    descricao   VARCHAR(200) NOT NULL,
    ativo       BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em   TIMESTAMP    NOT NULL DEFAULT NOW()
);

INSERT INTO bid_modulo (codigo, descricao) VALUES
    ('fluxo',     'Fluxo e Movimentação de Leitos'),
    ('ocupacao',  'Ocupação de Leitos'),
    ('cirurgia',  'Cirurgias'),
    ('emergencia','Consultas de Emergência / Assistenciais')
ON CONFLICT (codigo) DO NOTHING;

-- Registro de cada BID salvo
CREATE TABLE IF NOT EXISTS bid_registro (
    id              SERIAL PRIMARY KEY,
    modulo_codigo   VARCHAR(50)  NOT NULL,
    data_referencia DATE         NOT NULL,   -- data do BID (ontem)
    data_geracao    TIMESTAMP    NOT NULL DEFAULT NOW(),
    usuario         VARCHAR(100) NOT NULL,
    observacao      TEXT,
    UNIQUE (modulo_codigo, data_referencia)
);

-- Dados de fluxo por setor (um registro por setor/dia)
CREATE TABLE IF NOT EXISTS bid_fluxo (
    id                      SERIAL PRIMARY KEY,
    bid_registro_id         INTEGER      NOT NULL REFERENCES bid_registro(id) ON DELETE CASCADE,
    str_cod                 VARCHAR(20)  NOT NULL,
    unidade                 VARCHAR(200) NOT NULL,
    capacidade              INTEGER,
    ocupacao_inicial        INTEGER      NOT NULL DEFAULT 0,
    admissao                INTEGER      NOT NULL DEFAULT 0,
    transferencia_entrada   INTEGER      NOT NULL DEFAULT 0,
    transferencia_saida     INTEGER      NOT NULL DEFAULT 0,
    alta_medica             INTEGER      NOT NULL DEFAULT 0,
    transferencia_externa   INTEGER      NOT NULL DEFAULT 0,
    evasao                  INTEGER      NOT NULL DEFAULT 0,
    obito                   INTEGER      NOT NULL DEFAULT 0,
    ocupacao_final          INTEGER      NOT NULL DEFAULT 0,
    -- Flags indicando se o valor foi editado manualmente
    editado                 BOOLEAN      NOT NULL DEFAULT FALSE,
    observacao              TEXT,
    UNIQUE (bid_registro_id, str_cod)
);

-- Auditoria de edições manuais
CREATE TABLE IF NOT EXISTS bid_edicao (
    id              SERIAL PRIMARY KEY,
    bid_fluxo_id    INTEGER      NOT NULL REFERENCES bid_fluxo(id) ON DELETE CASCADE,
    campo           VARCHAR(100) NOT NULL,
    valor_original  INTEGER,
    valor_editado   INTEGER,
    usuario         VARCHAR(100) NOT NULL,
    editado_em      TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- Ocupação diária por setor (histórico)
CREATE TABLE IF NOT EXISTS bid_ocupacao (
    id              SERIAL PRIMARY KEY,
    data_referencia DATE         NOT NULL,
    str_cod         VARCHAR(20)  NOT NULL,
    unidade         VARCHAR(200) NOT NULL,
    capacidade      INTEGER,
    ocupados        INTEGER      NOT NULL DEFAULT 0,
    coletado_em     TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (data_referencia, str_cod)
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_bid_registro_data    ON bid_registro (data_referencia);
CREATE INDEX IF NOT EXISTS idx_bid_fluxo_registro   ON bid_fluxo    (bid_registro_id);
CREATE INDEX IF NOT EXISTS idx_bid_ocupacao_data    ON bid_ocupacao  (data_referencia);
