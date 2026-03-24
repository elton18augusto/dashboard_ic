SELECT
	ff.data AS data_feriado,
	ff.Nome AS feriado
FROM 
	FeriadoFranquia ff
WHERE
	ff.CodigoFranquia = :cod_franquia
	AND ff.DataDelete IS NULL
	AND YEAR(ff.`Data`) = :ano
	AND MONTH(ff.`Data`) = :mes;