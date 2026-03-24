SELECT
    base.dt,
    COALESCE(l.vendedor, c.vendedor) AS vendedor,
    COALESCE(curso.Nome,'Outros') AS curso_agrupado,
    COALESCE(l.midia, c.midia, 'Outros') AS midia,    

    IFNULL(l.qtd_leads,0) AS qtd_leads,
    IFNULL(c.qtd_contratos,0) AS qtd_contratos,
    IFNULL(c.vl_faturado,0) AS vl_faturado,
    IFNULL(c.vl_recebido,0) AS vl_recebido,
    IFNULL(c.tempo_med_conversao, 0) AS tempo_med_conversao,

    ROUND(
        IFNULL(c.qtd_contratos,0) / NULLIF(l.qtd_leads,0) * 100
    ,2) AS conversao

FROM (

    /* base vendedor + curso + dia (contato + contrato) */

    SELECT dt, cod_vendedor, cod_curso_agrupado, midia
    FROM (

        SELECT
            DATE(c.DataInsert) AS dt,
            vnd.Codigo AS cod_vendedor,
            md.Descricao AS midia,
            map.cod_curso_agrupado

        FROM Contato c

        LEFT JOIN Midia md ON md.Codigo = c.CodigoMidia

        LEFT JOIN CursoLead cl
            ON cl.Codigo = c.CodigoCurso

        LEFT JOIN (
            SELECT 69 AS Codigo_curso_lead,52 AS cod_curso_agrupado
            UNION ALL SELECT 66,47
            UNION ALL SELECT 32,25
            UNION ALL SELECT 43,35
            UNION ALL SELECT 23,4
            UNION ALL SELECT 28,57
            UNION ALL SELECT 34,27
            UNION ALL SELECT 38,34
            UNION ALL SELECT 20,NULL
            UNION ALL SELECT 40,NULL
            UNION ALL SELECT 37,NULL
            UNION ALL SELECT 35,29
            UNION ALL SELECT 56,41
            UNION ALL SELECT 75,NULL
            UNION ALL SELECT 70,NULL
            UNION ALL SELECT 10,NULL
            UNION ALL SELECT 7,NULL
            UNION ALL SELECT 81,21
            UNION ALL SELECT 2,11
            UNION ALL SELECT 47,NULL
            UNION ALL SELECT 63,43
            UNION ALL SELECT 65,45
            UNION ALL SELECT 57,NULL
            UNION ALL SELECT 22,NULL
            UNION ALL SELECT 80,NULL
            UNION ALL SELECT 54,40
            UNION ALL SELECT 79,NULL
            UNION ALL SELECT 73,40
            UNION ALL SELECT 21,NULL
            UNION ALL SELECT 45,5
        ) map
            ON map.Codigo_curso_lead = cl.Codigo

        LEFT JOIN Pessoa vnd
            ON vnd.Codigo = c.CodigoPessoaVendedor

        WHERE
            c.CodigoFranquia = :cod_franquia
            AND YEAR(c.DataInsert) = :ano
            AND MONTH(c.DataInsert) = :mes

        GROUP BY
            DATE(c.DataInsert),
            vnd.Codigo,
            md.Codigo,
            map.cod_curso_agrupado

        UNION

        SELECT
            DATE(cnt.DataInsert) AS dt,
            vnd.Codigo AS cod_vendedor,
            md.Descricao AS midia,
            ca.Codigo AS cod_curso_agrupado

        FROM Contrato cnt
        
        LEFT JOIN Contato c ON c.Codigo = cnt.CodigoContato        
        LEFT JOIN Midia md ON md.Codigo = c.CodigoMidia
        

        INNER JOIN ContratoCurso cc
            ON cc.CodigoContrato = cnt.Codigo

        INNER JOIN Curso cur
            ON cur.Codigo = cc.CodigoCurso

        LEFT JOIN CursoAgrupado ca
            ON ca.Codigo = cur.CodigoCursoAgrupado

        LEFT JOIN Colaborador col
            ON col.Codigo = cnt.CodigoColaboradorConsultor

        LEFT JOIN Pessoa vnd
            ON vnd.Codigo = col.CodigoPessoa

        WHERE
            cnt.CodigoFranquia = :cod_franquia
            AND cnt.DataDelete IS NULL
            AND cc.DataDelete IS NULL
            AND YEAR(cnt.DataInsert) = :ano
            AND MONTH(cnt.DataInsert) = :mes

        GROUP BY
            DATE(cnt.DataInsert),
            vnd.Codigo,
            md.Codigo,
            ca.Codigo

    ) base_union

) base


LEFT JOIN (

    /* leads por dia */

    SELECT
        DATE(c.DataInsert) AS dt,
        vnd.Codigo AS cod_vendedor,
        vnd.NomePessoaNomeFantasia AS vendedor,
        map.cod_curso_agrupado,
        md.Descricao AS midia,
        COUNT(DISTINCT c.Codigo) AS qtd_leads

    FROM Contato c
    
    LEFT JOIN Midia md 
	 	ON md.Codigo = c.CodigoMidia

    LEFT JOIN CursoLead cl
        ON cl.Codigo = c.CodigoCurso

    LEFT JOIN (
            SELECT 69 AS Codigo_curso_lead, 52 AS cod_curso_agrupado
            UNION ALL SELECT 66,47
            UNION ALL SELECT 32,25
            UNION ALL SELECT 43,35
            UNION ALL SELECT 23,4
            UNION ALL SELECT 28,57
            UNION ALL SELECT 34,27
            UNION ALL SELECT 38,34
            UNION ALL SELECT 20,NULL
            UNION ALL SELECT 40,NULL
            UNION ALL SELECT 37,NULL
            UNION ALL SELECT 35,29
            UNION ALL SELECT 56,41
            UNION ALL SELECT 75,NULL
            UNION ALL SELECT 70,NULL
            UNION ALL SELECT 10,NULL
            UNION ALL SELECT 7,NULL
            UNION ALL SELECT 81,21
            UNION ALL SELECT 2,11
            UNION ALL SELECT 47,NULL
            UNION ALL SELECT 63,43
            UNION ALL SELECT 65,45
            UNION ALL SELECT 57,NULL
            UNION ALL SELECT 22,NULL
            UNION ALL SELECT 80,NULL
            UNION ALL SELECT 54,40
            UNION ALL SELECT 79,NULL
            UNION ALL SELECT 73,40
            UNION ALL SELECT 21,NULL
            UNION ALL SELECT 45,5
        ) map
            ON map.Codigo_curso_lead = cl.Codigo

    LEFT JOIN Pessoa vnd
        ON vnd.Codigo = c.CodigoPessoaVendedor

    WHERE
        c.CodigoFranquia = :cod_franquia
        AND YEAR(c.DataInsert) = :ano
        AND MONTH(c.DataInsert) = :mes

    GROUP BY
        DATE(c.DataInsert),
        vnd.Codigo,
        md.Descricao,
        map.cod_curso_agrupado

) l
    ON l.cod_vendedor <=> base.cod_vendedor
   AND l.cod_curso_agrupado <=> base.cod_curso_agrupado
   AND l.dt = base.dt
   AND l.midia <=> base.midia


LEFT JOIN (

    /* contratos por dia */

    SELECT
        DATE(cnt.DataInsert) AS dt,
        vnd.Codigo AS cod_vendedor,
        vnd.NomePessoaNomeFantasia AS vendedor,
        ca.Codigo AS cod_curso_agrupado,
        md.Descricao AS midia,

        COUNT(DISTINCT cnt.Codigo) AS qtd_contratos,
        SUM(cf.Valor + cf.ValorAcrescimo + cf.ValorDesconto) AS vl_faturado,
        SUM(IFNULL(mf_agg.vl_recebido, 0)) as vl_recebido,
        -- SUM(
        --     CASE
        --         WHEN YEAR(mf.DataMovimentacao) = :ano
        --              AND MONTH(mf.DataMovimentacao) = :mes
        --         THEN mf.Valor
        --         ELSE 0
        --     END
        -- ) AS vl_recebido,
        AVG(DATEDIFF(cnt.DataInsert, c.DataInsert)) AS tempo_med_conversao

    FROM Contrato cnt
    
    LEFT JOIN Contato c ON c.Codigo = cnt.CodigoContato
    LEFT JOIN Midia md ON md.Codigo = c.CodigoMidia

    INNER JOIN ContratoCurso cc
        ON cc.CodigoContrato = cnt.Codigo

    INNER JOIN Curso cur
        ON cur.Codigo = cc.CodigoCurso

    LEFT JOIN CursoAgrupado ca
        ON ca.Codigo = cur.CodigoCursoAgrupado

    LEFT JOIN ContaFranquia cf
        ON cf.CodigoContrato = cnt.Codigo

    LEFT JOIN Colaborador col
        ON col.Codigo = cnt.CodigoColaboradorConsultor

    LEFT JOIN Pessoa vnd
        ON vnd.Codigo = col.CodigoPessoa

    -- LEFT JOIN MovimentacaoFranquia mf
    --     ON mf.CodigoContaFranquia = cf.Codigo 

    LEFT JOIN (
        SELECT
            CodigoContaFranquia,
            SUM(Valor) AS vl_recebido
        FROM MovimentacaoFranquia
        WHERE
            DataDelete IS NULL
            AND (Excluida = 'N' OR Excluida IS NULL)
            AND YEAR(DataMovimentacao) = :ano
            AND MONTH(DataMovimentacao) = :mes
        GROUP BY CodigoContaFranquia
    ) mf_agg
        ON mf_agg.CodigoContaFranquia = cf.Codigo

    WHERE
        cnt.CodigoFranquia = :cod_franquia
        AND cnt.DataDelete IS NULL
        AND cc.DataDelete IS NULL
        AND cf.DataDelete IS NULL
        -- AND mf.DataDelete IS NULL
        -- AND (mf.Excluida = 'N' OR mf.Excluida IS NULL)
        AND cnt.CodigoStatusContrato NOT IN (3,9)
        AND cf.CodigoTipoContaFranquia <> 55
        AND YEAR(cnt.DataInsert) = :ano
        AND MONTH(cnt.DataInsert) = :mes

    GROUP BY
        DATE(cnt.DataInsert),
        vnd.Codigo,
        md.Codigo,
        ca.Codigo

) c
    ON c.cod_vendedor <=> base.cod_vendedor
   AND c.cod_curso_agrupado <=> base.cod_curso_agrupado
   AND c.dt = base.dt
   AND c.midia <=> base.midia


LEFT JOIN CursoAgrupado curso
    ON curso.Codigo = base.cod_curso_agrupado


ORDER BY
    base.dt,
    vendedor,
    curso_agrupado,
	 midia;