"""
Utilidades Compartidas de Filtrado de DataFrames
=================================================

Módulo que consolida toda la lógica de filtrado de datos para las aplicaciones
de administración y usuario. Proporciona una interfaz unificada para filtrar
DataFrames de Pandas por diferentes criterios.

Funcionalidades:
- Filtrado por valores de columnas (con soporte case-insensitive)
- Búsqueda de texto en múltiples columnas
- Filtrado por rangos de fechas
- Filtros combinados (estado, prioridad, territorial, búsqueda)
- Filtrado por condiciones personalizadas (funciones lambda)

Uso típico:
    ```python
    from shared_filter_utils import DataFrameFilterUtil

    # Filtrar por múltiples criterios
    df_filtrado = DataFrameFilterUtil.apply_filters(
        df,
        estado=['Asignada', 'En Proceso'],
        search_term='Juan'
    )
    ```

Autor: Equipo IGAC
Fecha: 2024-2025
"""

from typing import List, Optional, Callable
import pandas as pd


class DataFrameFilterUtil:
    """
    Utilidad unificada para filtrado de DataFrames

    Consolida todos los patrones de filtrado usados en las aplicaciones de
    administración y usuario. Proporciona una interfaz consistente para
    filtrar datos según diferentes criterios.

    Todos los métodos son estáticos ya que no mantienen estado interno.
    Cada método retorna un nuevo DataFrame filtrado sin modificar el original.
    """

    @staticmethod
    def filter_by_column_values(
        df: pd.DataFrame,
        column: str,
        values: List,
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """
        Filtrar DataFrame verificando si el valor de la columna está en una lista

        Args:
            df (pd.DataFrame): DataFrame a filtrar
            column (str): Nombre de la columna a filtrar
            values (List): Lista de valores permitidos
            case_sensitive (bool): Si la comparación de strings es sensible a mayúsculas.
                                  Por defecto False (insensible a mayúsculas)

        Returns:
            pd.DataFrame: DataFrame filtrado conteniendo solo filas donde el valor
                         de la columna coincide con alguno de los valores proporcionados

        Ejemplo:
            ```python
            # Filtrar solicitudes en estado Asignada o En Proceso
            df_filtrado = DataFrameFilterUtil.filter_by_column_values(
                df, 'estado', ['Asignada', 'En Proceso']
            )
            ```

        Nota:
            - Si la lista de valores está vacía, retorna el DataFrame completo
            - Si la columna no existe, retorna el DataFrame completo sin filtrar
            - Para columnas de tipo string, soporta comparación case-insensitive
        """
        if not values or column not in df.columns:
            return df

        if case_sensitive:
            # Comparación exacta (sensible a mayúsculas/minúsculas)
            return df[df[column].isin(values)]
        else:
            # Para columnas de texto, hacer comparación insensible a mayúsculas
            if df[column].dtype == 'object':
                return df[df[column].str.lower().isin([v.lower() for v in values])]
            else:
                # Para columnas numéricas u otros tipos, comparación directa
                return df[df[column].isin(values)]

    @staticmethod
    def filter_by_text_search(
        df: pd.DataFrame,
        search_term: str,
        columns: List[str],
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """
        Filtrar DataFrame buscando texto en múltiples columnas

        Realiza búsqueda de texto parcial (substring) en las columnas especificadas.
        Usa condición OR: retorna filas donde el texto se encuentra en CUALQUIERA
        de las columnas especificadas.

        Args:
            df (pd.DataFrame): DataFrame a filtrar
            search_term (str): Texto a buscar (búsqueda parcial, no exacta)
            columns (List[str]): Lista de nombres de columnas donde buscar
            case_sensitive (bool): Si la búsqueda es sensible a mayúsculas.
                                  Por defecto False (insensible)

        Returns:
            pd.DataFrame: DataFrame filtrado con filas que contienen el término
                         de búsqueda en al menos una de las columnas especificadas

        Ejemplo:
            ```python
            # Buscar "Juan" en nombre o ID de solicitud
            df_filtrado = DataFrameFilterUtil.filter_by_text_search(
                df, 'Juan', ['nombre_solicitante', 'id_solicitud']
            )
            ```

        Nota:
            - La búsqueda es de substring (encuentra "Juan" en "Juan Pérez")
            - Valores None/NaN se tratan como False (no coinciden)
            - Columnas que no existen se ignoran silenciosamente
        """
        if not search_term or not columns:
            return df

        # Crear máscara con condición OR entre todas las columnas
        mask = pd.Series([False] * len(df), index=df.index)

        for column in columns:
            if column in df.columns:
                # Convertir a string y buscar (ignora NaN automáticamente)
                mask |= df[column].astype(str).str.contains(
                    search_term,
                    case=case_sensitive,
                    na=False  # NaN se trata como no coincidente
                )

        return df[mask]

    @staticmethod
    def apply_filters(
        df: pd.DataFrame,
        estado: Optional[List[str]] = None,
        prioridad: Optional[List[str]] = None,
        territorial: Optional[List[str]] = None,
        search_term: Optional[str] = None,
        search_columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aplicar múltiples filtros al DataFrame de forma combinada

        Función de conveniencia que aplica varios filtros comunes en una sola llamada.
        Los filtros se aplican secuencialmente usando condición AND (todos deben cumplirse).

        Args:
            df (pd.DataFrame): DataFrame a filtrar
            estado (Optional[List[str]]): Lista de estados a incluir
                                         (ej: ['Asignada', 'En Proceso'])
            prioridad (Optional[List[str]]): Lista de prioridades a incluir
                                            (ej: ['Alta', 'Media'])
            territorial (Optional[List[str]]): Lista de territoriales a incluir
                                              (ej: ['Bogotá', 'Antioquia'])
            search_term (Optional[str]): Término de búsqueda de texto
            search_columns (Optional[List[str]]): Columnas donde buscar el término.
                                                 Por defecto: ['id_solicitud', 'nombre_solicitante']

        Returns:
            pd.DataFrame: DataFrame filtrado aplicando todos los criterios especificados

        Ejemplo:
            ```python
            # Filtrar solicitudes asignadas o en proceso, búsqueda de "Juan"
            df_filtrado = DataFrameFilterUtil.apply_filters(
                df,
                estado=['Asignada', 'En Proceso'],
                search_term='Juan',
                search_columns=['nombre_solicitante']
            )
            ```

        Nota:
            - Los filtros se aplican en orden: estado, prioridad, territorial, búsqueda
            - Si un parámetro es None, ese filtro se omite
            - Los filtros usan condición AND (deben cumplirse todos)
        """
        df_filtered = df.copy()

        # Aplicar filtros por valor de columna
        if estado:
            df_filtered = DataFrameFilterUtil.filter_by_column_values(
                df_filtered, 'estado', estado
            )

        if prioridad:
            df_filtered = DataFrameFilterUtil.filter_by_column_values(
                df_filtered, 'prioridad', prioridad
            )

        if territorial:
            df_filtered = DataFrameFilterUtil.filter_by_column_values(
                df_filtered, 'territorial', territorial
            )

        # Aplicar búsqueda de texto
        if search_term:
            # Si no se especifican columnas, usar las por defecto
            if search_columns is None:
                search_columns = ['id_solicitud', 'nombre_solicitante']

            df_filtered = DataFrameFilterUtil.filter_by_text_search(
                df_filtered, search_term, search_columns
            )

        return df_filtered

    @staticmethod
    def filter_by_date_range(
        df: pd.DataFrame,
        column: str,
        start_date,
        end_date
    ) -> pd.DataFrame:
        """
        Filtrar DataFrame por rango de fechas

        Filtra filas donde la fecha en la columna especificada está dentro del
        rango proporcionado (ambos límites inclusivos).

        Args:
            df (pd.DataFrame): DataFrame a filtrar
            column (str): Nombre de la columna con fechas a filtrar
            start_date: Fecha inicial del rango (inclusiva)
            end_date: Fecha final del rango (inclusiva)

        Returns:
            pd.DataFrame: DataFrame filtrado con fechas dentro del rango especificado

        Ejemplo:
            ```python
            from datetime import date
            start = date(2024, 1, 1)
            end = date(2024, 12, 31)

            df_filtrado = DataFrameFilterUtil.filter_by_date_range(
                df, 'fecha_solicitud', start, end
            )
            ```

        Nota:
            - Si la columna no existe, retorna el DataFrame completo
            - Si start_date o end_date son NaN/None, retorna el DataFrame completo
            - El rango es inclusivo en ambos extremos
            - Requiere que la columna sea de tipo datetime
        """
        if column not in df.columns:
            return df

        # Solo filtrar si ambas fechas son válidas
        if pd.notna(start_date) and pd.notna(end_date):
            df_filtered = df[
                (df[column].dt.date >= start_date) &
                (df[column].dt.date <= end_date)
            ]
            return df_filtered

        return df

    @staticmethod
    def filter_by_condition(
        df: pd.DataFrame,
        condition_func: Callable[[pd.DataFrame], pd.Series]
    ) -> pd.DataFrame:
        """
        Filtrar DataFrame usando una función de condición personalizada

        Permite aplicar lógica de filtrado arbitraria mediante una función lambda
        o función definida que retorna una Serie booleana.

        Args:
            df (pd.DataFrame): DataFrame a filtrar
            condition_func (Callable): Función que recibe el DataFrame y retorna
                                      una Serie booleana indicando qué filas mantener

        Returns:
            pd.DataFrame: DataFrame filtrado según la condición personalizada.
                         Si hay error, retorna el DataFrame original.

        Ejemplo:
            ```python
            # Filtrar solicitudes pausadas más de 7 días
            df_filtrado = DataFrameFilterUtil.filter_by_condition(
                df, lambda df: df['tiempo_pausado_dias'] > 7
            )

            # Filtrar solicitudes completadas en diciembre
            df_filtrado = DataFrameFilterUtil.filter_by_condition(
                df,
                lambda df: (df['estado'] == 'Completada') &
                          (df['fecha_completado'].dt.month == 12)
            )
            ```

        Nota:
            - La función debe retornar una Serie booleana del mismo tamaño que el DataFrame
            - Si la función genera un error, se registra y se retorna el DataFrame original
            - Útil para condiciones complejas que no tienen método específico
        """
        try:
            mask = condition_func(df)
            return df[mask]
        except Exception as e:
            print(f"⚠️ Error aplicando filtro personalizado: {e}")
            return df
