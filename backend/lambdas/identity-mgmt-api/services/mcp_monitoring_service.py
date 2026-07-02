"""
MCP Monitoring Service
======================
Servicio de monitorización del servidor MCP de Remedy F1.

Lee los logs del servicio ECS desde CloudWatch Logs (Logs Insights). NO requiere
base de datos ni cambios de infraestructura: aprovecha que el servidor MCP emite
una línea estructurada por invocación de herramienta (prefijo "MCP_USAGE").

El servidor MCP NO se ve obligado a escribir en RDS; toda la métrica se deriva de
sus logs, que ya existen.
"""

import logging
import os
import time
from typing import Dict, Any, List

import boto3

logger = logging.getLogger()

# Log group del servicio ECS del MCP (sandbox eu-west-1).
DEFAULT_LOG_GROUP = '/ecs/nedgi-kb-dev-remedy-mcp'


class MCPMonitoringService:
    """Consulta métricas de uso del MCP desde CloudWatch Logs Insights."""

    def __init__(self):
        self.region = os.environ.get('MCP_LOG_REGION', os.environ.get('AWS_REGION', 'eu-west-1'))
        self.log_group = os.environ.get('MCP_LOG_GROUP', DEFAULT_LOG_GROUP)
        self.client = boto3.client('logs', region_name=self.region)

    def _run_query(self, query_string: str, hours: int, limit: int = 1000) -> List[Dict[str, str]]:
        """Ejecutar una consulta de Logs Insights y devolver filas como dicts."""
        end = int(time.time())
        start = end - hours * 3600

        try:
            start_resp = self.client.start_query(
                logGroupName=self.log_group,
                startTime=start,
                endTime=end,
                queryString=query_string,
                limit=limit
            )
            query_id = start_resp['queryId']

            # Polling hasta que termine (Logs Insights es asíncrono).
            for _ in range(30):  # ~15s máx
                resp = self.client.get_query_results(queryId=query_id)
                if resp['status'] in ('Complete', 'Failed', 'Cancelled'):
                    break
                time.sleep(0.5)

            if resp['status'] != 'Complete':
                logger.warning(f"Consulta Logs Insights terminó en estado {resp['status']}")
                return []

            rows = []
            for result in resp.get('results', []):
                rows.append({field['field']: field['value'] for field in result})
            return rows
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(f"Log group {self.log_group} no encontrado todavía")
            return []
        except Exception as e:
            logger.error(f"Error consultando CloudWatch Logs: {e}")
            return []

    def get_usage_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Resumen: invocaciones totales, errores y desglose por herramienta."""
        # El servidor MCP emite: "MCP_USAGE tool=<x> user=<email> status=<ok|error>"
        by_tool = self._run_query(
            'fields @message '
            '| filter @message like "MCP_USAGE" '
            '| parse @message "tool=* " as tool '
            '| stats count(*) as invocations by tool '
            '| sort invocations desc',
            hours=hours
        )

        status_rows = self._run_query(
            'fields @message '
            '| filter @message like "MCP_USAGE" '
            '| parse @message "status=*" as status '
            '| stats count(*) as count by status',
            hours=hours
        )

        total = sum(int(r.get('invocations', 0)) for r in by_tool)
        errors = sum(int(r.get('count', 0)) for r in status_rows
                     if r.get('status', '').startswith('error'))

        return {
            'period_hours': hours,
            'total_invocations': total,
            'total_errors': errors,
            'by_tool': by_tool,
            'by_status': status_rows
        }

    def get_usage_by_user(self, hours: int = 24) -> Dict[str, Any]:
        """Invocaciones agrupadas por usuario (email del JWT)."""
        rows = self._run_query(
            'fields @message '
            '| filter @message like "MCP_USAGE" '
            '| parse @message "user=* " as user '
            '| stats count(*) as invocations by user '
            '| sort invocations desc',
            hours=hours
        )
        return {'period_hours': hours, 'by_user': rows}

    def get_recent_activity(self, hours: int = 24, limit: int = 50) -> Dict[str, Any]:
        """Últimas invocaciones (para una tabla de actividad reciente)."""
        rows = self._run_query(
            'fields @timestamp, @message '
            '| filter @message like "MCP_USAGE" '
            '| sort @timestamp desc',
            hours=hours,
            limit=limit
        )
        return {'period_hours': hours, 'events': rows}
