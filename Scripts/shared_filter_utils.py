"""
Shared DataFrame filtering utilities for both Admin and User apps
Consolidates filtering logic that's repeated across multiple files
"""
from typing import List, Optional, Callable
import pandas as pd


class DataFrameFilterUtil:
    """Unified DataFrame filtering utility

    Consolidates all filtering patterns used in both admin and user apps.
    Provides consistent filtering interface across the application.
    """

    @staticmethod
    def filter_by_column_values(
        df: pd.DataFrame,
        column: str,
        values: List,
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """Filter DataFrame by checking if column value is in list

        Args:
            df: DataFrame to filter
            column: Column name to filter on
            values: List of values to match
            case_sensitive: Whether string comparison is case-sensitive

        Returns:
            Filtered DataFrame

        Example:
            df_filtered = DataFrameFilterUtil.filter_by_column_values(
                df, 'estado', ['Asignada', 'En Proceso']
            )
        """
        if not values or column not in df.columns:
            return df

        if case_sensitive:
            return df[df[column].isin(values)]
        else:
            # For string columns, do case-insensitive comparison
            if df[column].dtype == 'object':
                return df[df[column].str.lower().isin([v.lower() for v in values])]
            else:
                return df[df[column].isin(values)]

    @staticmethod
    def filter_by_text_search(
        df: pd.DataFrame,
        search_term: str,
        columns: List[str],
        case_sensitive: bool = False
    ) -> pd.DataFrame:
        """Filter DataFrame by searching text in multiple columns

        Args:
            df: DataFrame to filter
            search_term: Text to search for
            columns: List of column names to search in
            case_sensitive: Whether string comparison is case-sensitive

        Returns:
            Filtered DataFrame with rows matching search term

        Example:
            df_filtered = DataFrameFilterUtil.filter_by_text_search(
                df, 'Juan', ['nombre_solicitante', 'id_solicitud']
            )
        """
        if not search_term or not columns:
            return df

        # Create mask for OR condition across multiple columns
        mask = pd.Series([False] * len(df), index=df.index)

        for column in columns:
            if column in df.columns:
                mask |= df[column].astype(str).str.contains(
                    search_term,
                    case=case_sensitive,
                    na=False
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
        """Apply multiple filters to DataFrame

        Combines multiple filter types for convenience.

        Args:
            df: DataFrame to filter
            estado: List of estados to include
            prioridad: List of prioridades to include
            territorial: List of territoriales to include
            search_term: Text to search for
            search_columns: Columns to search in (defaults to ['id_solicitud', 'nombre_solicitante'])

        Returns:
            Filtered DataFrame

        Example:
            df_filtered = DataFrameFilterUtil.apply_filters(
                df,
                estado=['Asignada', 'En Proceso'],
                search_term='Juan',
                search_columns=['nombre_solicitante']
            )
        """
        df_filtered = df.copy()

        # Apply column value filters
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

        # Apply text search
        if search_term:
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
        """Filter DataFrame by date range

        Args:
            df: DataFrame to filter
            column: Date column to filter on
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Filtered DataFrame

        Example:
            df_filtered = DataFrameFilterUtil.filter_by_date_range(
                df, 'fecha_solicitud', start_date, end_date
            )
        """
        if column not in df.columns:
            return df

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
        """Filter DataFrame using custom condition function

        Args:
            df: DataFrame to filter
            condition_func: Function that takes DataFrame and returns boolean Series

        Returns:
            Filtered DataFrame

        Example:
            df_filtered = DataFrameFilterUtil.filter_by_condition(
                df, lambda df: df['tiempo_pausado_dias'] > 7
            )
        """
        try:
            mask = condition_func(df)
            return df[mask]
        except Exception as e:
            print(f"⚠️ Error applying custom filter: {e}")
            return df
