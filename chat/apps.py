# chat/apps.py
from django.apps import AppConfig
import logging
import sys
import os
logger = logging.getLogger(__name__)


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        try:
            import chat.signals
            if not any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'shell']):
                from cassandra.cqlengine import connection
                from cassandra.cqlengine.management import sync_table, create_keyspace_simple
                hosts = ['127.0.0.1']
                keyspace = 'galileo'
                protocol = 4
                port = int(os.getenv('SCYLLA_PORT', 9042))  # Ensure integer
                logger.debug(f"Setting up ScyllaDB: hosts={hosts}, keyspace={keyspace}, protocol={protocol}, port={port}, type(port)={type(port)}")
                connection.setup(hosts, default_keyspace=keyspace, protocol_version=protocol, port=port)
                create_keyspace_simple('galileo', replication_factor=1)
                from .models import MessageScylla
                sync_table(MessageScylla)
                logger.info("ScyllaDB connection established")
        except Exception as e:
            logger.error(f"ScyllaDB setup error: {str(e)}")