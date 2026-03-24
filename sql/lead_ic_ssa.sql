SELECT
	DATE(c.DataInsert) AS data_lead,
	st.Descricao AS status_lead,
	cl.Codigo as cod_curso_lead,
	cl.Nome AS curso_lead,
	md.Descricao AS midia_lead,
	cmp.Descricao AS campanha_lead,
	vnd.Codigo as cod_vendedor,
	vnd.NomePessoaNomeFantasia AS vendedor
FROM 
	Contato c
	INNER JOIN Midia md ON md.Codigo = c.CodigoMidia
	LEFT JOIN Campanha cmp ON cmp.Codigo = c.CodigoCampanha
	LEFT JOIN Status st ON st.Codigo = c.CodigoStatus
	LEFT JOIN CursoLead cl ON cl.Codigo = c.CodigoCurso
	LEFT JOIN Pessoa vnd ON vnd.Codigo = c.CodigoPessoaVendedor
WHERE
	c.CodigoFranquia = 119
	AND DATE(c.DataInsert) BETWEEN :data_inicio AND :data_fim;