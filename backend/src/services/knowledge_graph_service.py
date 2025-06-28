"""
Neo4j Knowledge Graph Service for Charleston County Property Data
"""
import logging
from neo4j import GraphDatabase
from datetime import datetime
from typing import Dict, List, Optional
from src.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

class CharlestonKnowledgeGraph:
    """Manages Neo4j knowledge graph for Charleston County property data"""
    
    def __init__(self):
        self.driver = None
        self.connect()
    
    def connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
            logger.info("Connected to Neo4j knowledge graph")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def create_property_node(self, tms_number: str, pin: str = None) -> bool:
        """Create or merge a property node"""
        try:
            with self.driver.session() as session:
                query = """
                MERGE (p:Property {tms_number: $tms_number, pin: $pin})
                SET p.created_at = datetime()
                SET p.updated_at = datetime()
                RETURN p
                """
                result = session.run(query, tms_number=tms_number, pin=pin or tms_number)
                logger.info(f"Created/updated property node: {tms_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to create property node: {e}")
            return False
    
    def create_property_card_node(self, tms_number: str, url: str, saved_as: str = "Property Card") -> bool:
        """Create property card node and link to property"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})
                MERGE (pc:PropertyCard:Document {
                    url: $url, 
                    saved_as: $saved_as,
                    type: 'property_card',
                    downloaded: true
                })
                SET pc.created_at = datetime()
                MERGE (p)-[:HAS]->(pc)
                RETURN pc
                """
                result = session.run(query, tms_number=tms_number, url=url, saved_as=saved_as)
                logger.info(f"Created property card node for TMS: {tms_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to create property card node: {e}")
            return False
    
    def create_tax_info_node(self, tms_number: str, url: str, saved_as: str = "Tax Info") -> bool:
        """Create tax info node and link to property"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})
                MERGE (ti:TaxInfo:Document {
                    url: $url, 
                    saved_as: $saved_as,
                    type: 'tax_info',
                    downloaded: true
                })
                SET ti.created_at = datetime()
                MERGE (p)-[:HAS]->(ti)
                MERGE (p)-[:HAS_TAX_INFO]->(ti)
                RETURN ti
                """
                result = session.run(query, tms_number=tms_number, url=url, saved_as=saved_as)
                logger.info(f"Created tax info node for TMS: {tms_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to create tax info node: {e}")
            return False
    
    def create_transaction_and_deed(self, tms_number: str, transaction_date: str, 
                                   book: str, page: str, pdf_url: str = None, 
                                   saved_as: str = None) -> bool:
        """Create transaction and deed nodes with relationships"""
        try:
            with self.driver.session() as session:
                # Create transaction
                transaction_query = """
                MATCH (p:Property {tms_number: $tms_number})
                MERGE (t:Transaction {date: $transaction_date, book: $book, page: $page})
                SET t.created_at = datetime()
                SET t.type = 'deed'
                MERGE (p)-[:HAS_TRANSACTION]->(t)
                RETURN t
                """
                session.run(transaction_query, 
                           tms_number=tms_number, 
                           transaction_date=transaction_date,
                           book=book, 
                           page=page)                    # Create deed if URL provided
                if pdf_url:
                    deed_saved_as = saved_as or f"DB {book} {page}"
                    deed_query = """
                    // First match the transaction
                    MATCH (t:Transaction {date: $transaction_date, book: $book, page: $page})
                    
                    // Create the deed with proper labels and properties
                    MERGE (d:Deed:Document {
                        book_number: $book, 
                        page_number: $page, 
                        pdf_url: $pdf_url, 
                        saved_as: $saved_as,
                        type: 'deed',
                        downloaded: true,
                        pdf_path: $pdf_url
                    })
                    SET d.created_at = datetime()
                    MERGE (t)-[:REFERENCES]->(d)
                    
                    // Use WITH to pass values between query parts
                    WITH d, t, $book as book, $page as page, $tms_number as tms
                    
                    // Create book and page structure
                    MERGE (b:Book {number: book})
                    MERGE (pg:Page {number: page})
                    MERGE (d)-[:STORED_IN]->(b)
                    MERGE (b)-[:HAS_PAGE]->(pg)
                    
                    // Connect deed to property using WITH to pass variables
                    WITH d, tms
                    MATCH (p:Property {tms_number: tms})
                    MERGE (p)-[:HAS]->(d)
                    
                    RETURN d
                    """
                    session.run(deed_query,
                               transaction_date=transaction_date,
                               book=book,
                               page=page,
                               pdf_url=pdf_url,
                               saved_as=deed_saved_as,
                               tms_number=tms_number)
                
                logger.info(f"Created transaction and deed for TMS: {tms_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to create transaction and deed: {e}")
            return False
    
    def get_property_data(self, tms_number: str) -> Dict:
        """Get all property data from knowledge graph"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})
                OPTIONAL MATCH (p)-[:HAS]->(pc:PropertyCard)
                OPTIONAL MATCH (p)-[:HAS_TAX_INFO]->(ti:TaxInfo)
                OPTIONAL MATCH (p)-[:HAS_TRANSACTION]->(t:Transaction)
                OPTIONAL MATCH (t)-[:REFERENCES]->(d:Deed)
                RETURN p, pc, ti, collect(t) as transactions, collect(d) as deeds
                """
                result = session.run(query, tms_number=tms_number)
                record = result.single()
                
                if record:
                    return {
                        "property": dict(record["p"]),
                        "property_card": dict(record["pc"]) if record["pc"] else None,
                        "tax_info": dict(record["ti"]) if record["ti"] else None,
                        "transactions": [dict(t) for t in record["transactions"]],
                        "deeds": [dict(d) for d in record["deeds"]]
                    }
                return {}
        except Exception as e:
            logger.error(f"Failed to get property data: {e}")
            return {}
    
    def search_properties_by_book_page(self, book: str, page: str) -> List[Dict]:
        """Search properties by deed book and page"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (d:Deed {book_number: $book, page_number: $page})
                MATCH (t:Transaction)-[:REFERENCES]->(d)
                MATCH (p:Property)-[:HAS_TRANSACTION]->(t)
                RETURN p, t, d
                """
                results = session.run(query, book=book, page=page)
                
                properties = []
                for record in results:
                    properties.append({
                        "property": dict(record["p"]),
                        "transaction": dict(record["t"]),
                        "deed": dict(record["d"])
                    })
                return properties
        except Exception as e:
            logger.error(f"Failed to search properties by book/page: {e}")
            return []
    
    def store_workflow_state(self, tms_number: str, step: str, status: str, data: Dict = None) -> bool:
        """Store workflow state in knowledge graph"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})
                MERGE (ws:WorkflowState {property_tms: $tms_number, step: $step})
                SET ws.status = $status
                SET ws.updated_at = datetime()
                SET ws.data = $data
                MERGE (p)-[:HAS_WORKFLOW_STATE]->(ws)
                RETURN ws
                """
                session.run(query, 
                           tms_number=tms_number, 
                           step=step, 
                           status=status, 
                           data=data or {})
                return True
        except Exception as e:
            logger.error(f"Failed to store workflow state: {e}")
            return False
        
    def store_workflow_instructions(self, phase: str, instructions: dict) -> bool:
        """
        Store workflow phase instructions in Neo4j as 3rd fallback
        Args:
            phase: Workflow phase name (e.g., "search_form", "extract_deed")
            instructions: Dictionary of instructions for the phase
        Returns:
            bool: Success status
        """
        import json
        try:
            instructions_json = json.dumps(instructions)
            with self.driver.session() as session:
                query = """
                MERGE (w:WorkflowPhase {name: $phase})
                SET w.instructions = $instructions,
                    w.updated_at = datetime()
                RETURN w
                """
                session.run(query, phase=phase, instructions=instructions_json)
            logger.info(f"Stored workflow instructions for phase: {phase}")
            return True
        except Exception as e:
            logger.error(f"Failed to store workflow instructions: {e}")
            return False

    def get_workflow_instructions(self, phase: str) -> dict:
        """
        Retrieve workflow phase instructions from Neo4j as 3rd fallback
        Args:
            phase: Workflow phase name
        Returns:
            dict: Instructions for the workflow phase
        """
        import json
        try:
            with self.driver.session() as session:
                query = """
                MATCH (w:WorkflowPhase {name: $phase})
                RETURN w.instructions as instructions
                """
                result = session.run(query, phase=phase)
                record = result.single()
                if not record or not record["instructions"]:
                    logger.warning(f"No instructions found for workflow phase: {phase}")
                    return {"error": "No instructions found", "fallback_action": "continue"}
                instructions = json.loads(record["instructions"])
                logger.info(f"Retrieved workflow instructions for phase: {phase}")
                return instructions
        except Exception as e:
            logger.error(f"Failed to retrieve workflow instructions: {e}")
            return {"error": str(e), "fallback_action": "retry"}
    
    def get_pending_deed_downloads(self) -> List:
        """Get all deed references that haven't been downloaded yet"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (t:Transaction)-[:REFERENCES]->(d:Deed)
                WHERE d.downloaded IS NULL OR d.downloaded = false
                RETURN d.book_number as book, d.page_number as page, t.date as date, d.property_id as property_id
                ORDER BY date DESC
                """
                result = session.run(query)
                records = [record for record in result]
                logger.info(f"Found {len(records)} pending deed downloads")
                return records
        except Exception as e:
            logger.error(f"Failed to get pending deed downloads: {e}")
            return []
    
    def mark_deed_as_downloaded(self, book: str, page: str, pdf_path: str) -> bool:
        """Mark a deed as successfully downloaded"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (d:Deed {book_number: $book, page_number: $page})
                SET d.downloaded = true
                SET d.downloaded_at = datetime()
                SET d.pdf_path = $pdf_path
                RETURN d
                """
                result = session.run(query, book=book, page=page, pdf_path=pdf_path)
                logger.info(f"Marked deed {book}-{page} as downloaded: {pdf_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to mark deed as downloaded: {e}")
            return False
            
    def schedule_periodic_deed_check(self, tms_number: str, check_interval_days: int = 30) -> bool:
        """Schedule a property for periodic deed checking"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})
                SET p.periodic_check = true
                SET p.check_interval_days = $check_interval_days
                SET p.next_check_date = datetime().plus(duration({days: $check_interval_days}))
                RETURN p
                """
                result = session.run(query, tms_number=tms_number, check_interval_days=check_interval_days)
                logger.info(f"Scheduled periodic deed check for TMS {tms_number} every {check_interval_days} days")
                return True
        except Exception as e:
            logger.error(f"Failed to schedule periodic deed check: {e}")
            return False
            
    def get_properties_due_for_check(self) -> List:
        """Get all properties that are due for a periodic deed check"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property)
                WHERE p.periodic_check = true 
                  AND p.next_check_date <= datetime()
                RETURN p.tms_number as tms_number, p.check_interval_days as check_interval_days
                """
                result = session.run(query)
                records = [record for record in result]
                logger.info(f"Found {len(records)} properties due for deed check")
                return records
        except Exception as e:
            logger.error(f"Failed to get properties due for check: {e}")
            return []
    
    def get_all_properties_with_deeds(self) -> List:
        """Get all properties that have deed references in the database"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property)-[:HAS_TRANSACTION]->(:Transaction)-[:REFERENCES]->(:Deed)
                RETURN DISTINCT p.tms_number as tms_number, 
                       p.check_interval_days as check_interval_days,
                       count(DISTINCT d) as deed_count
                """
                result = session.run(query)
                records = [record for record in result]
                logger.info(f"Found {len(records)} properties with deed references")
                return records
        except Exception as e:
            logger.error(f"Failed to get properties with deeds: {e}")
            return []
            
    def get_property_deed_references(self, tms_number: str) -> List:
        """Get all known deed references for a specific property"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})-[:HAS_TRANSACTION]->(t:Transaction)-[:REFERENCES]->(d:Deed)
                RETURN t.date as date, d.book_number as book, d.page_number as page, 
                       d.downloaded as downloaded, d.pdf_path as pdf_path
                """
                result = session.run(query, tms_number=tms_number)
                records = [record for record in result]
                logger.info(f"Found {len(records)} deed references for TMS {tms_number}")
                return records
        except Exception as e:
            logger.error(f"Failed to get deed references for TMS {tms_number}: {e}")
            return []
    
    def get_all_deed_book_pages(self) -> List:
        """Get all book and page numbers for all properties in the database"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property)-[:HAS_TRANSACTION]->(:Transaction)-[:REFERENCES]->(d:Deed)
                RETURN p.tms_number as tms_number, d.book_number as book, d.page_number as page, 
                       d.downloaded as downloaded, d.pdf_path as pdf_path
                ORDER BY tms_number, book, page
                """
                result = session.run(query)
                records = [record for record in result]
                logger.info(f"Found {len(records)} total deed book/page references")
                return records
        except Exception as e:
            logger.error(f"Failed to get all deed book/page references: {e}")
            return []
    
    def get_deeds_pending_download(self) -> List:
        """Get all deed references that have not yet been downloaded"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property)-[:HAS_TRANSACTION]->(:Transaction)-[:REFERENCES]->(d:Deed)
                WHERE d.downloaded IS NULL OR d.downloaded = false
                RETURN p.tms_number as tms_number, d.book_number as book, d.page_number as page
                ORDER BY tms_number, book, page
                """
                result = session.run(query)
                records = [record for record in result]
                logger.info(f"Found {len(records)} deed references pending download")
                return records
        except Exception as e:
            logger.error(f"Failed to get pending deed downloads: {e}")
            return []
    
    def store_deed_references(self, tms_number: str, deed_references: List[Dict]) -> bool:
        """Store deed references in Neo4j for efficient tracking and retrieval
        
        This helps track which deeds need to be collected without re-parsing HTML
        """
        try:
            with self.driver.session() as session:
                # First, make sure property node exists
                property_query = """
                MERGE (p:Property {tms_number: $tms_number})
                RETURN p
                """
                session.run(property_query, tms_number=tms_number)
                
                # For each deed reference, create a DeedReference node
                count = 0
                for deed_ref in deed_references:
                    book = deed_ref.get('book', '')
                    page = deed_ref.get('page', '')
                    if not book or not page:
                        continue
                        
                    # Create additional properties dict
                    properties = {
                        'book': book,
                        'page': page,
                        'source': deed_ref.get('source', 'unknown'),
                        'year': deed_ref.get('year', ''),
                        'grantor': deed_ref.get('grantor', ''),
                        'grantee': deed_ref.get('grantee', ''),
                        'date': deed_ref.get('date', ''),
                        'deed_type': deed_ref.get('deed_type', ''),
                        'confidence': deed_ref.get('confidence', 0.0),
                        'extracted_by': deed_ref.get('extracted_by', 'unknown')
                    }
                    
                    # Only include price if present and not zero
                    if deed_ref.get('price') and deed_ref.get('price') != '0':
                        properties['price'] = deed_ref.get('price')
                    
                    # Store in graph
                    deed_ref_query = """
                    MATCH (p:Property {tms_number: $tms_number})
                    MERGE (d:DeedReference {book: $book, page: $page})
                    SET d += $properties
                    SET d.created_at = datetime()
                    MERGE (p)-[:HAS_DEED_REFERENCE]->(d)
                    RETURN d
                    """
                    session.run(
                        deed_ref_query,
                        tms_number=tms_number,
                        book=book,
                        page=page,
                        properties=properties
                    )
                    count += 1
                
                logger.info(f"Stored {count} deed references for TMS: {tms_number}")
                return True
        except Exception as e:
            logger.error(f"Failed to store deed references: {e}")
            return False
            
    def get_stored_deed_references(self, tms_number: str) -> List[Dict]:
        """Retrieve stored deed references from Neo4j"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (p:Property {tms_number: $tms_number})-[:HAS_DEED_REFERENCE]->(d:DeedReference)
                RETURN d
                ORDER BY d.year DESC, d.book DESC
                """
                result = session.run(query, tms_number=tms_number)
                
                deed_refs = []
                for record in result:
                    deed_ref = dict(record["d"])
                    deed_refs.append(deed_ref)
                
                logger.info(f"Retrieved {len(deed_refs)} deed references for TMS: {tms_number}")
                return deed_refs
        except Exception as e:
            logger.error(f"Failed to retrieve deed references: {e}")
            return []
    
    def update_deed_status(self, tms_number: str, book: str, page: str, 
                         status: str = "downloaded") -> bool:
        """
        Update the download status of a deed in Neo4j
        
        Args:
            tms_number: Property TMS number
            book: Deed book number
            page: Deed page number
            status: New status (e.g., "downloaded", "pending", "failed")
            
        Returns:
            bool: Success of the operation
        """
        try:
            with self.driver.session() as session:
                # Update existing deed if it exists
                deed_query = """
                MATCH (p:Property {tms_number: $tms_number})
                MATCH (d:Deed {book_number: $book, page_number: $page})
                SET d.status = $status
                SET d.updated_at = datetime()
                RETURN d
                """
                result = session.run(
                    deed_query,
                    tms_number=tms_number,
                    book=book,
                    page=page,
                    status=status
                )
                
                # Check if deed was found and updated
                summary = result.consume()
                if summary.counters.properties_set > 0:
                    logger.info(f"Updated deed status to '{status}' for Book {book}, Page {page}")
                    return True
                else:
                    # No deed found, create a placeholder with status
                    placeholder_query = """
                    MATCH (p:Property {tms_number: $tms_number})
                    MERGE (d:Deed {book_number: $book, page_number: $page})
                    SET d.status = $status
                    SET d.created_at = datetime()
                    SET d.updated_at = datetime()
                    SET d.type = 'deed'
                    WITH d, p
                    MERGE (p)-[:HAS]->(d)
                    RETURN d
                    """
                    
                    session.run(
                        placeholder_query,
                        tms_number=tms_number,
                        book=book,
                        page=page,
                        status=status
                    )
                    
                    logger.info(f"Created deed placeholder with status '{status}' for Book {book}, Page {page}")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update deed status: {e}")
            return False
        
    def get_all_deeds_for_property(self, tms_number: str):
        """Get all deeds associated with a property"""
        try:
            query = """
            MATCH (p:Property {tms_number: $tms_number})-[:HAS_DEED]->(d:Deed)
            RETURN d
            """
            with self.driver.session() as session:
                result = session.run(query, tms_number=tms_number)
                return list(result.data())
        except Exception as e:
            logger.error(f"Error retrieving deeds for property {tms_number}: {e}")
            return []
