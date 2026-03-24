SELECT 
	mf.CodigoFranquia AS cod_franquia,
	YEAR(mf.MesAnoReferencia) AS ano_meta,
	MONTH(mf.MesAnoReferencia) AS mes_meta,
	mfc.CodigoCursoAgrupado AS cod_curso_agrupado,
	ca.Nome AS curso_agrupado,
	mfc.QtdVendasFranquia AS meta_qtd,
	mfc.ValorVendasFranquia AS meta_fat
	
FROM 
	MetaFranquia mf
	LEFT JOIN MetaFranquiaCursoAgrupado mfc ON mfc.CodigoMetaFranquia = mf.Codigo
	LEFT JOIN CursoAgrupado ca ON ca.Codigo = mfc.CodigoCursoAgrupado
WHERE
	mf.CodigoFranquia = :cod_franquia
	AND YEAR(mf.MesAnoReferencia) = :ano
	AND MONTH(mf.MesAnoReferencia) = :mes
	AND mf.DataDelete IS NULL 
	AND mfc.DataDelete IS NULL;
