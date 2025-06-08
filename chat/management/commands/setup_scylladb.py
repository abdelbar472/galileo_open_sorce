# chat/management/commands/setup_scylladb.py
from django.core.management.base import BaseCommand
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table, create_keyspace_simple
from chat.models import MessageScylla
import logging
import time
import os

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Set up ScyllaDB connection and sync tables'

    def handle(self, *args, **options):
        max_retries = 5
        retry_delay = 5  # seconds
        hosts = ['127.0.0.1']
        keyspace = 'galileo'
        protocol = 4
        port = int(os.getenv('SCYLLA_PORT', 9042))  # Ensure integer

        for attempt in range(max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}: Connecting with hosts={hosts}, keyspace={keyspace}, protocol={protocol}, port={port}, type(port)={type(port)}")
                connection.setup(hosts, default_keyspace=keyspace, protocol_version=protocol, port=port)
                create_keyspace_simple('galileo', replication_factor=1)
                sync_table(MessageScylla)
                logger.info("ScyllaDB connection established and tables synced")
                self.stdout.write(self.style.SUCCESS("ScyllaDB setup completed"))
                return
            except Exception as e:
                logger.error(f"ScyllaDB setup attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    self.stdout.write(self.style.ERROR("Failed to set up ScyllaDB after retries"))
                    raise