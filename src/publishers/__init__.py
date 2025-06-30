from typing import Dict

from src.publishers.delta import delta_publish
from src.publishers.publisher import ENGINE_FUNC
from src.publishers.starrocks import starrocks_publish
from src.pyetl import PublishType

publishingEngines: Dict[PublishType, ENGINE_FUNC] = {
    PublishType.DELTA: delta_publish,
    PublishType.WAREHOUSE: starrocks_publish,
}
