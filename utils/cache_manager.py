# utils/cache_manager.py
import streamlit as st
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    """Gestor avanzado de caché para la aplicación."""
    
    def __init__(self, default_ttl: int = 1800):  # 30 minutos por defecto
        self.default_ttl = default_ttl
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "total_requests": 0
        }
    
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """
        Obtiene un valor del caché.
        
        Args:
            key: Clave del caché
            ttl: Tiempo de vida en segundos (opcional)
            
        Returns:
            Valor almacenado o None si no existe o expiró
        """
        self._cache_stats["total_requests"] += 1
        
        cache_key = f"cache_{key}"
        
        if cache_key in st.session_state:
            cache_data = st.session_state[cache_key]
            
            # Verificar expiración
            expiration = cache_data.get("expiration")
            if expiration and datetime.now() > expiration:
                # Cache expirado
                del st.session_state[cache_key]
                self._cache_stats["misses"] += 1
                logger.debug(f"Cache expirado para clave: {key}")
                return None
            
            # Cache hit
            self._cache_stats["hits"] += 1
            logger.debug(f"Cache hit para clave: {key}")
            return cache_data["value"]
        
        # Cache miss
        self._cache_stats["misses"] += 1
        logger.debug(f"Cache miss para clave: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Almacena un valor en el caché.
        
        Args:
            key: Clave del caché
            value: Valor a almacenar
            ttl: Tiempo de vida en segundos (opcional)
        """
        cache_key = f"cache_{key}"
        ttl = ttl or self.default_ttl
        
        cache_data = {
            "value": value,
            "created": datetime.now(),
            "expiration": datetime.now() + timedelta(seconds=ttl),
            "ttl": ttl
        }
        
        st.session_state[cache_key] = cache_data
        logger.debug(f"Cache set para clave: {key} (TTL: {ttl}s)")
    
    def invalidate(self, key: str):
        """
        Invalida una entrada del caché.
        
        Args:
            key: Clave del caché a invalidar
        """
        cache_key = f"cache_{key}"
        
        if cache_key in st.session_state:
            del st.session_state[cache_key]
            self._cache_stats["invalidations"] += 1
            logger.debug(f"Cache invalidado para clave: {key}")
            return True
        
        return False
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalida todas las entradas del caché que coincidan con un patrón.
        
        Args:
            pattern: Patrón a buscar en las claves
        """
        keys_to_remove = []
        
        for key in st.session_state.keys():
            if key.startswith("cache_") and pattern in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del st.session_state[key]
            self._cache_stats["invalidations"] += 1
        
        logger.debug(f"Cache invalidado para patrón: {pattern} ({len(keys_to_remove)} entradas)")
        return len(keys_to_remove)
    
    def clear_all(self):
        """Limpia todo el caché."""
        keys_to_remove = [key for key in st.session_state.keys() if key.startswith("cache_")]
        
        for key in keys_to_remove:
            del st.session_state[key]
        
        self._cache_stats["invalidations"] += len(keys_to_remove)
        logger.info(f"Cache limpiado completamente ({len(keys_to_remove)} entradas)")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            Diccionario con estadísticas
        """
        total = self._cache_stats["total_requests"]
        hits = self._cache_stats["hits"]
        misses = self._cache_stats["misses"]
        
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        return {
            "total_requests": total,
            "hits": hits,
            "misses": misses,
            "invalidations": self._cache_stats["invalidations"],
            "hit_rate": f"{hit_rate:.1f}%",
            "current_size": len([k for k in st.session_state.keys() if k.startswith("cache_")])
        }
    
    def get_keys(self) -> list:
        """
        Obtiene todas las claves del caché.
        
        Returns:
            Lista de claves
        """
        return [k.replace("cache_", "") for k in st.session_state.keys() if k.startswith("cache_")]
    
    def cleanup_expired(self):
        """Limpia las entradas expiradas del caché."""
        expired_keys = []
        now = datetime.now()
        
        for key in st.session_state.keys():
            if key.startswith("cache_"):
                cache_data = st.session_state[key]
                expiration = cache_data.get("expiration")
                
                if expiration and now > expiration:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del st.session_state[key]
        
        if expired_keys:
            logger.debug(f"Limpieza de cache: {len(expired_keys)} entradas expiradas removidas")
        
        return len(expired_keys)

# Instancia global del cache manager
cache_manager = CacheManager()

# Funciones helper para uso rápido
def get_cache() -> CacheManager:
    """Retorna la instancia global del cache manager."""
    return cache_manager

def cached_function(ttl: int = 1800):
    """
    Decorador para cachear resultados de funciones.
    
    Args:
        ttl: Tiempo de vida en segundos
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Crear clave única basada en función y argumentos
            func_name = func.__name__
            args_key = str(args) + str(sorted(kwargs.items()))
            cache_key = f"{func_name}_{hash(args_key)}"
            
            # Intentar obtener del caché
            cached_value = cache_manager.get(cache_key, ttl)
            
            if cached_value is not None:
                return cached_value
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator