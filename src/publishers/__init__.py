from typing import Dict

from servc_typings.domains.publisher import PublishType

from src.publishers.delta import delta_publish
from src.publishers.publisher import ENGINE_FUNC
from src.publishers.starrocks import starrocks_publish

publishingEngines: Dict[PublishType, ENGINE_FUNC] = {
    PublishType.DELTA: delta_publish,
    PublishType.WAREHOUSE: starrocks_publish,
}
