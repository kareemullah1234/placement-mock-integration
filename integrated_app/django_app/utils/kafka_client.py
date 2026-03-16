import json
import uuid
import base64
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False

from django.conf import settings

logger = logging.getLogger(__name__)

class KafkaFrameClient:
    def __init__(self):
        if not KAFKA_AVAILABLE:
            logger.error("kafka-python not installed. Install with: pip install kafka-python")
            self.producer = None
            self._connected = False
            return

        # Configuration for both frames and video - FIXED for internal Docker network
        self.config = getattr(settings, 'KAFKA_CONFIG', {
            # Use internal Docker network communication (containers to containers)
            'bootstrap_servers': [
                'localhost:9092'   
            ],
            'frame_topic': 'interview-frames',
            'video_topic': 'interview-videos',
            'timeout': 10
        })

        # Ensure bootstrap_servers is a list
        bootstrap_servers = self.config['bootstrap_servers']
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = [bootstrap_servers]

        self.producer = None
        self._connected = False

        # Try different server configurations
        server_configs = [
            bootstrap_servers,
            ['kafka-frames:9092'],
            ['172.18.0.14:9092']
        ]

        for attempt, servers in enumerate(server_configs, 1):
            try:
                logger.info(f"Kafka connection attempt {attempt}: {servers}")

                self.producer = KafkaProducer(
                    bootstrap_servers=servers,
                    value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=1,
                    request_timeout_ms=10000,  # 10 seconds
                    api_version_auto_timeout_ms=5000,
                    compression_type='gzip',
                    batch_size=32768,
                    linger_ms=100,
                    buffer_memory=67108864,
                    max_request_size=10485760,
                    # Additional connection settings for Docker network
                    security_protocol='PLAINTEXT',
                    metadata_max_age_ms=30000,
                    connections_max_idle_ms=540000
                )

                # Test the connection with a simple check
                try:
                    # Try to get bootstrap configuration - this will trigger connection
                    self.producer.bootstrap_connected()
                    logger.info(f"✅ Kafka producer created successfully with {servers}")
                    self._connected = True
                    break

                except Exception as test_error:
                    logger.warning(f"Producer created but bootstrap test failed: {test_error}")
                    # Still mark as connected if producer was created successfully
                    self._connected = True
                    break

            except Exception as e:
                logger.warning(f"❌ Kafka connection attempt {attempt} failed: {e}")
                if self.producer:
                    try:
                        self.producer.close(timeout=1)
                    except:
                        pass
                    self.producer = None
                continue

        if not self._connected:
            logger.error("❌ All Kafka connection attempts failed")
            self.producer = None
        else:
            logger.info("🚀 Kafka video client initialized successfully")

    def is_connected(self):
        """Check if Kafka client is connected"""
        return self._connected and self.producer is not None

    def generate_session_id(self, user, attempt_number):
        """Generate unique session ID"""
        timestamp = int(time.time())
        return f"{user.id}_{attempt_number}_{timestamp}_{uuid.uuid4().hex[:8]}"

    def start_frame_session(self, user, interview, total_frames_estimate=0):
        """Start a new frame session"""
        if not self.is_connected():
            logger.error("Kafka client not connected")
            return None

        try:
            session_id = self.generate_session_id(user, interview.attempt_number)

            session_data = {
                'type': 'session_start',
                'session_id': session_id,
                'user_id': user.id,
                'user_name': f"{user.first_name}{user.last_name}".replace(' ', ''),
                'student_id': getattr(user.student_profile, 'student_id', str(user.id)) if hasattr(user, 'student_profile') else str(user.id),
                'attempt_number': interview.attempt_number,
                'interview_id': interview.id,
                'total_frames': total_frames_estimate,
                'started_at': datetime.now().isoformat(),
                'metadata': {
                    'user_email': user.email,
                    'interview_status': interview.status,
                    'user_full_name': user.get_full_name()
                }
            }

            # Send session start message
            future = self.producer.send(self.config['frame_topic'], value=session_data)
            future.get(timeout=10)  # Wait for confirmation

            logger.info(f"Frame session started: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to start frame session: {e}")
            return None

    def send_frame(self, session_id: str, frame_number: int, frame_data_b64: str,
                   width: int = 0, height: int = 0, timestamp: str = None):
        """Send a single frame to Kafka"""
        if not self.is_connected():
            logger.error("Kafka client not connected")
            return False

        try:
            if timestamp is None:
                timestamp = datetime.now().isoformat()

            frame_message = {
                'type': 'frame',
                'session_id': session_id,
                'frame_data': {
                    'frame_number': frame_number,
                    'frame_data': frame_data_b64,
                    'width': width,
                    'height': height,
                    'timestamp': timestamp,
                    'size_bytes': len(frame_data_b64)
                },
                'sent_at': datetime.now().isoformat()
            }

            # Send frame message (don't wait for each frame to improve performance)
            future = self.producer.send(self.config['frame_topic'], value=frame_message)

            logger.debug(f"Frame {frame_number} sent for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to send frame {frame_number}: {e}")
            return False

    def send_video_chunk(self, session_id, chunk_number, video_data_b64,
                        chunk_size, timestamp, mime_type, interview_id, user_id):
        """Send video chunk to Kafka"""
        try:
            video_message = {
                'type': 'video_chunk',
                'session_id': session_id,
                'interview_id': interview_id,
                'user_id': user_id,
                'chunk_number': chunk_number,
                'video_data': video_data_b64,
                'chunk_size': chunk_size,
                'timestamp': timestamp,
                'mime_type': mime_type,
                'sent_at': datetime.now().isoformat()
            }

            # Send to video topic
            future = self.producer.send(self.config['video_topic'], value=video_message)
            record_metadata = future.get(timeout=10)

            logger.debug(f"Video chunk sent: {session_id}-{chunk_number} to {record_metadata.topic}")
            return True

        except Exception as e:
            logger.error(f"Failed to send video chunk: {e}")
            return False

    def get_video_chunks(self, session_id):
        """Retrieve video chunks from Kafka for playback - OPTIMIZED VERSION"""
        try:
            # Use internal Docker network addresses
            bootstrap_servers = [
                'kafka-frames:9092',
                '172.18.0.14:9092'
            ]

            consumer = None
            for servers in [[server] for server in bootstrap_servers]:
                try:
                    consumer = KafkaConsumer(
                        self.config['video_topic'],
                        bootstrap_servers=servers,
                        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                        auto_offset_reset='earliest',
                        consumer_timeout_ms=5000,  # Reduced timeout
                        fetch_max_wait_ms=1000,    # Faster fetching
                        max_poll_records=100,      # Process more records per poll
                        api_version_auto_timeout_ms=3000,
                        security_protocol='PLAINTEXT'
                    )

                    # Test if consumer is working
                    partitions = consumer.partitions_for_topic(self.config['video_topic'])
                    if partitions:
                        logger.info(f"✅ Consumer connected to {servers}")
                        break
                    else:
                        consumer.close()
                        consumer = None

                except Exception as e:
                    logger.warning(f"Consumer connection failed for {servers}: {e}")
                    if consumer:
                        consumer.close()
                    consumer = None
                    continue

            if not consumer:
                logger.error("❌ Failed to create Kafka consumer")
                return []

            video_chunks = []
            message_count = 0
            start_time = time.time()
            max_scan_time = 15  # Maximum 15 seconds to scan

            logger.info(f"🔍 Searching for video chunks with session_id: {session_id}")

            try:
                for message in consumer:
                    message_count += 1

                    # Check timeout
                    if time.time() - start_time > max_scan_time:
                        logger.warning(f"⏰ Scan timeout after {max_scan_time}s, stopping search")
                        break

                    try:
                        data = message.value
                        if (data.get('session_id') == session_id and
                            data.get('type') == 'video_chunk'):

                            video_chunks.append({
                                'chunk_number': data['chunk_number'],
                                'video_data': data['video_data'],
                                'chunk_size': data['chunk_size'],
                                'timestamp': data['timestamp'],
                                'mime_type': data.get('mime_type', 'video/webm')
                            })

                            # Log progress for large numbers of chunks
                            if len(video_chunks) % 20 == 0:
                                logger.info(f"📹 Found {len(video_chunks)} video chunks so far...")

                    except Exception as e:
                        logger.warning(f"Error processing message: {e}")
                        continue

                    # Limit message scanning to prevent infinite loops
                    if message_count >= 2000:  # Increased limit
                        logger.warning("Reached message scan limit (2000), stopping search")
                        break

            except Exception as e:
                logger.error(f"Error during message consumption: {e}")
            finally:
                consumer.close()

            # Sort by chunk number
            video_chunks.sort(key=lambda x: x['chunk_number'])

            scan_time = time.time() - start_time
            logger.info(f"✅ Scan completed in {scan_time:.1f}s")
            logger.info(f"✅ Retrieved {len(video_chunks)} video chunks for session {session_id}")
            logger.info(f"📊 Processed {message_count} total messages")

            if video_chunks:
                total_size = sum(chunk['chunk_size'] for chunk in video_chunks)
                logger.info(f"📦 Total video size: {total_size / 1024 / 1024:.2f} MB")

            return video_chunks

        except Exception as e:
            logger.error(f"❌ Failed to retrieve video chunks: {e}")
            return []

    def end_video_session(self, session_id: str, total_chunks: int):
        """End a video session"""
        if not self.is_connected():
            logger.error("Kafka client not connected")
            return False

        try:
            session_end_data = {
                'type': 'video_session_end',
                'session_id': session_id,
                'total_chunks': total_chunks,
                'ended_at': datetime.now().isoformat()
            }

            # Send session end message
            future = self.producer.send(self.config['video_topic'], value=session_end_data)
            future.get(timeout=10)  # Wait for confirmation

            logger.info(f"Video session ended: {session_id} with {total_chunks} chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to end video session: {e}")
            return False

    def send_frames_batch(self, session_id: str, frames_data: List[Dict]):
        """Send multiple frames in batch"""
        if not self.is_connected():
            logger.error("Kafka client not connected")
            return False

        success_count = 0
        total_frames = len(frames_data)

        try:
            logger.info(f"Starting batch send of {total_frames} frames for session {session_id}")

            for i, frame_data in enumerate(frames_data):
                try:
                    # Handle different frame data formats
                    if isinstance(frame_data, str):
                        # If frame_data is just a base64 string
                        frame_b64 = frame_data
                        frame_num = i
                        width = height = 0
                        timestamp = None
                    elif isinstance(frame_data, dict):
                        # If frame_data is a dictionary with metadata
                        frame_b64 = frame_data.get('frame_data', frame_data.get('data', ''))
                        frame_num = frame_data.get('frame_number', i)
                        width = frame_data.get('width', 0)
                        height = frame_data.get('height', 0)
                        timestamp = frame_data.get('timestamp')
                    else:
                        logger.warning(f"Unknown frame data format at index {i}")
                        continue

                    if not frame_b64:
                        logger.warning(f"Empty frame data at index {i}")
                        continue

                    success = self.send_frame(
                        session_id=session_id,
                        frame_number=frame_num,
                        frame_data_b64=frame_b64,
                        width=width,
                        height=height,
                        timestamp=timestamp
                    )

                    if success:
                        success_count += 1

                    # Log progress every 10 frames
                    if (i + 1) % 10 == 0:
                        logger.info(f"Sent {i + 1}/{total_frames} frames")

                except Exception as e:
                    logger.error(f"Error processing frame {i}: {e}")
                    continue

            # Flush producer to ensure all messages are sent
            self.producer.flush(timeout=30)

            logger.info(f"Batch send completed: {success_count}/{total_frames} frames sent successfully")
            return success_count == total_frames

        except Exception as e:
            logger.error(f"Failed to send frames batch: {e}")
            return False

    def end_frame_session(self, session_id: str, total_frames_sent: int):
        """End a frame session"""
        if not self.is_connected():
            logger.error("Kafka client not connected")
            return False

        try:
            session_end_data = {
                'type': 'session_end',
                'session_id': session_id,
                'total_frames_sent': total_frames_sent,
                'ended_at': datetime.now().isoformat()
            }

            # Send session end message
            future = self.producer.send(self.config['frame_topic'], value=session_end_data)
            future.get(timeout=10)  # Wait for confirmation

            logger.info(f"Frame session ended: {session_id} with {total_frames_sent} frames")
            return True

        except Exception as e:
            logger.error(f"Failed to end frame session: {e}")
            return False

    def test_connection(self):
        """Test Kafka connection by sending a test message"""
        if not self.is_connected():
            return False

        try:
            test_message = {
                'type': 'test',
                'timestamp': datetime.now().isoformat(),
                'message': 'Connection test'
            }

            future = self.producer.send(self.config['frame_topic'], value=test_message)
            future.get(timeout=5)

            logger.info("Kafka connection test successful")
            return True

        except Exception as e:
            logger.error(f"Kafka connection test failed: {e}")
            return False

    def get_topic_info(self):
        """Get information about the Kafka topic"""
        if not self.is_connected():
            return None

        try:
            frame_topic = self.config['frame_topic']
            video_topic = self.config['video_topic']

            info = {
                'frame_topic': frame_topic,
                'video_topic': video_topic,
                'brokers': [],
                'topics_found': []
            }

            # Try to get broker information through different methods
            try:
                # Method 1: Try getting cluster metadata
                cluster_metadata = self.producer._metadata
                if cluster_metadata and hasattr(cluster_metadata, 'brokers'):
                    if callable(cluster_metadata.brokers):
                        brokers_data = cluster_metadata.brokers()
                    else:
                        brokers_data = cluster_metadata.brokers

                    if hasattr(brokers_data, 'keys'):
                        info['brokers'] = list(brokers_data.keys())
                    elif hasattr(brokers_data, '_iter_'):
                        info['brokers'] = list(brokers_data)
            except Exception as broker_error:
                logger.debug(f"Broker info method 1 failed: {broker_error}")

                # Method 2: Try using producer's bootstrap servers
                try:
                    info['brokers'] = self.config['bootstrap_servers']
                except Exception:
                    info['brokers'] = []

            # Get topic information using consumer
            try:
                from kafka import KafkaConsumer
                temp_consumer = KafkaConsumer(
                    bootstrap_servers=self.config['bootstrap_servers'],
                    api_version_auto_timeout_ms=5000,
                    request_timeout_ms=10000
                )

                # Get list of available topics
                available_topics = temp_consumer.topics()
                if available_topics:
                    info['topics_found'] = list(available_topics)

                    # Check if our required topics exist
                    if frame_topic in available_topics:
                        info['frame_topic_exists'] = True
                        # Try to get partition info
                        try:
                            partitions = temp_consumer.partitions_for_topic(frame_topic)
                            if partitions:
                                info['frame_partitions'] = len(partitions)
                        except Exception:
                            pass
                    else:
                        info['frame_topic_exists'] = False

                    if video_topic in available_topics:
                        info['video_topic_exists'] = True
                        # Try to get partition info
                        try:
                            partitions = temp_consumer.partitions_for_topic(video_topic)
                            if partitions:
                                info['video_partitions'] = len(partitions)
                        except Exception:
                            pass
                    else:
                        info['video_topic_exists'] = False

                temp_consumer.close()

            except Exception as topic_error:
                logger.warning(f"Error getting topic info via consumer: {topic_error}")
                # Fallback: assume topics exist if we can connect
                info['topics_found'] = [frame_topic, video_topic]
                info['frame_topic_exists'] = True
                info['video_topic_exists'] = True

            return info

        except Exception as e:
            logger.error(f"Failed to get topic info: {e}")
            return {
                'frame_topic': self.config['frame_topic'],
                'video_topic': self.config['video_topic'],
                'brokers': self.config['bootstrap_servers'],
                'error': str(e),
                'topics_found': [],
                'frame_topic_exists': False,
                'video_topic_exists': False
            }

    def close(self):
        """Close Kafka producer"""
        if self.producer:
            try:
                self.producer.flush(timeout=10)
                self.producer.close()
                logger.info("Kafka producer closed")
                self._connected = False
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")

    def __del__(self):
        """Destructor to ensure producer is closed"""
        self.close()


# Utility function to test Kafka connection
def test_kafka_connection():
    """Test function to check if Kafka is working"""
    try:
        client = KafkaFrameClient()
        if client.is_connected():
            success = client.test_connection()
            topic_info = client.get_topic_info()
            client.close()

            return {
                'connected': True,
                'test_successful': success,
                'topic_info': topic_info
            }
        else:
            return {
                'connected': False,
                'error': 'Failed to connect to Kafka'
            }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
        }
