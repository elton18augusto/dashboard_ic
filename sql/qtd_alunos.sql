SELECT
    CONCAT(YEAR(ag.DataHoraInicio), '-', MONTH(ag.DataHoraInicio)) AS periodo,
    
    COUNT(DISTINCT CASE WHEN cur.Sigla = 'EL' THEN cnt.CodigoAluno END) AS el,
    COUNT(DISTINCT CASE WHEN cur.Sigla = 'PL' THEN cnt.CodigoAluno END) AS pl,
    COUNT(DISTINCT CASE WHEN cur.Sigla = 'ES' THEN cnt.CodigoAluno END) AS sol,
    COUNT(DISTINCT CASE WHEN cur.Sigla = 'CFTV' THEN cnt.CodigoAluno END) AS cftv,
    COUNT(DISTINCT CASE WHEN cur.Sigla IN ('PA', 'PAZ', 'PC') THEN cnt.CodigoAluno END) AS ped,
	 COUNT(DISTINCT CASE WHEN cur.Sigla = 'AR' THEN cnt.CodigoAluno END) AS ar,
	 COUNT(DISTINCT CASE WHEN cur.Sigla = 'MO' THEN cnt.CodigoAluno END) AS mo,
    COUNT(DISTINCT CASE WHEN cur.Sigla IN ('GA', 'GP', 'PO') THEN cnt.CodigoAluno END) AS gp,
    COUNT(DISTINCT CASE WHEN cur.Sigla IN ('PV', 'PVL', 'IPVL P') THEN cnt.CodigoAluno END) AS vn,
    COUNT(DISTINCT CASE WHEN cur.Sigla NOT IN ('EL', 'PL', 'ES', 'CFTV', 'PA', 'PAZ', 'PC', 'AR', 'MO', 'GA', 'GP', 'PO', 'PV', 'PVL', 'IPVL P') THEN cnt.CodigoAluno END) AS outros

FROM
    Contrato cnt
    INNER JOIN ContratoCurso cc ON cc.CodigoContrato = cnt.Codigo
    INNER JOIN Curso cur ON cur.Codigo = cc.CodigoCurso
    INNER JOIN ContratoCursoMateria ccm ON ccm.CodigoContratoCurso = cc.Codigo
    INNER JOIN Aula aul ON aul.CodigoContratoCursoMateria = ccm.Codigo
    INNER JOIN Agendamento ag ON ag.Codigo = aul.CodigoAgendamento

WHERE
    DATE(ag.DataHoraInicio) >= DATE(CONCAT(:ano, '-', :mes, '-01'))
    AND cnt.CodigoFranquia = :cod_franquia
    AND ag.Realizado = 'S'
    AND aul.PresencaFalta = 'P'

GROUP BY
    YEAR(ag.DataHoraInicio),
    MONTH(ag.DataHoraInicio)

ORDER BY
    periodo DESC;