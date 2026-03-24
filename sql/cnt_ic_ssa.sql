SELECT
	cnt.Codigo AS cod_contrato,
	cur.NomeSimplificado AS curso,
	ca.Codigo AS cod_curso_agrupado,
	ca.Nome AS curso_agrupado,
	md.Descricao AS midia_contrato,
	cmp.Descricao AS campanha_contrato,
	mdc.Descricao AS midia_lead,
	cmpc.Descricao AS campanha_lead,
	DATE(c.DataInsert) AS data_lead,
	DATE(cnt.DataInsert) AS data_contrato,
	SUM(cf.Valor + cf.ValorAcrescimo + cf.ValorDesconto) AS fat_curso,
	vnd.Codigo as cod_vendedor,
   vnd.NomePessoaNomeFantasia AS vendedor
FROM
	Contrato cnt
	LEFT JOIN Midia md ON cnt.CodigoMidia = md.Codigo
	LEFT JOIN Campanha cmp ON cmp.Codigo = cnt.CodigoCampanha
	LEFT JOIN Contato c ON c.Codigo = cnt.CodigoContato
	LEFT JOIN Midia mdc ON mdc.Codigo = cnt.CodigoMidia
	LEFT JOIN Campanha cmpc ON cmpc.Codigo = c.CodigoCampanha
	INNER JOIN ContratoCurso cc ON cc.CodigoContrato = cnt.Codigo
	INNER JOIN Curso cur ON cur.Codigo = cc.CodigoCurso
	LEFT JOIN ContaFranquia cf ON cf.CodigoContrato = cnt.Codigo
	LEFT JOIN Colaborador col ON col.Codigo = cnt.CodigoColaboradorConsultor
	LEFT JOIN Pessoa vnd ON vnd.Codigo = col.CodigoPessoa
	LEFT JOIN CursoAgrupado ca ON ca.Codigo = cur.CodigoCursoAgrupado
WHERE
	cnt.CodigoFranquia = 119
	AND cnt.DataDelete IS NULL
	AND cc.DataDelete IS NULL
	AND cf.DataDelete IS NULL
	AND cf.CodigoTipoContaFranquia <> 55
	AND DATE(cnt.DataInsert) BETWEEN :data_inicio AND :data_fim
GROUP BY
	cnt.Codigo;