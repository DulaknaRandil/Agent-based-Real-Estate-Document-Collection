"""
Test for Sales History table extraction and deed collection workflow
"""
import os
import sys
import json
from pathlib import Path

from src.services.gemini_service import GeminiService

def test_sales_history_extraction():
    """Test extraction from Sales History table HTML"""
    print("\n🔍 Testing Sales History table extraction")
    
    # Sample table HTML (from user input)
    sample_html = """
    <div id="lxT523" style="overflow: auto;"><!--Sales History | ProVal Sales History -->
    <!-- Bootstrap Header for ProVal General Info (Add Above Existing markup) -->
    <div class="container-fluid py-4">
        <div class="row bg-primary">
            <h2 class="col-sm-12 text-left text-light"><i style="font-size:1.2em;" class="bento-icon-users pr-3 text-light"></i>Sales History</h2>
        </div>
    </div>
    <!--end of header-->
    <table class="ui-widget-content ui-table" style="width:100%;">
    <tbody><tr>
    <th class="ui-widget ui-state-default center">Book</th> 
    <th class="ui-widget ui-state-default center">Page</th> 
    <th class="ui-widget ui-state-default center">Date</th> 
    <th class="ui-widget ui-state-default center">Grantor</th> 
    <th class="ui-widget ui-state-default center">Grantee</th> 
    <th class="ui-widget ui-state-default center">Type</th> 
    <th class="ui-widget ui-state-default center">Deed</th> 
    <th class="ui-widget ui-state-default center">Deed Price</th> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">1247    </td> 
    <td class="ui-widget ui-widget-content center">453     </td> 
    <td class="ui-widget ui-widget-content center">5/13/2024</td> 
    <td class="ui-widget ui-widget-content">FABIE JOSEPH ANDREW</td> 
    <td class="ui-widget ui-widget-content">PARADISE BRADLEY</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="Single">S </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$1,080,000</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">0799    </td> 
    <td class="ui-widget ui-widget-content center">591     </td> 
    <td class="ui-widget ui-widget-content center">6/3/2019</td> 
    <td class="ui-widget ui-widget-content">MURDOCH CHRISTOPHER JAMES</td> 
    <td class="ui-widget ui-widget-content">FABIE JOSEPH ANDREW</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="Single">S </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$500,000</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">0310    </td> 
    <td class="ui-widget ui-widget-content center">940     </td> 
    <td class="ui-widget ui-widget-content center">2/7/2013</td> 
    <td class="ui-widget ui-widget-content">ROTHWELL MATTHEW F</td> 
    <td class="ui-widget ui-widget-content">MURDOCH CHRISTOPHER JAMES</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="Single">S </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$315,000</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">0230    </td> 
    <td class="ui-widget ui-widget-content center">279     </td> 
    <td class="ui-widget ui-widget-content center">1/26/2012</td> 
    <td class="ui-widget ui-widget-content">CHANDLER MATTHEW B</td> 
    <td class="ui-widget ui-widget-content">ROTHWELL MATTHEW F</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="Single">S </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$310,000</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">0099    </td> 
    <td class="ui-widget ui-widget-content center">536     </td> 
    <td class="ui-widget ui-widget-content center">12/10/2008</td> 
    <td class="ui-widget ui-widget-content">CHANDLER MATTHEW B</td> 
    <td class="ui-widget ui-widget-content">CHANDLER MATTHEW B</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="">  </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$9</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">F226    </td> 
    <td class="ui-widget ui-widget-content center">146     </td> 
    <td class="ui-widget ui-widget-content center">4/27/1993</td> 
    <td class="ui-widget ui-widget-content">CAMP PAULA F</td> 
    <td class="ui-widget ui-widget-content">CHANDLER MATTHEW B</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="">  </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$140,000</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">W203    </td> 
    <td class="ui-widget ui-widget-content center">146     </td> 
    <td class="ui-widget ui-widget-content center">6/21/1991</td> 
    <td class="ui-widget ui-widget-content">SWILLEY NOVICE M</td> 
    <td class="ui-widget ui-widget-content">CAMP PAULA F</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="">  </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$123,000</td> 
    </tr><tr> 
    <td class="ui-widget ui-widget-content center">S111    </td> 
    <td class="ui-widget ui-widget-content center">290     </td> 
    <td class="ui-widget ui-widget-content center">2/28/1977</td> 
    <td class="ui-widget ui-widget-content"></td> 
    <td class="ui-widget ui-widget-content">SWILLEY NOVICE M</td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="">  </a></td> 
    <td class="ui-widget ui-widget-content center"><a href="#" onclick="return false" title="General Warranty Deed                                           ">Ge</a></td> 
    <td class="ui-widget ui-widget-content right">$0</td> 
    </tr></tbody></table></div>
    """
    
    # Initialize GeminiService
    gemini = GeminiService()
    
    # Test direct extraction
    print("Testing extract_sales_history_table:")
    references = gemini.extract_sales_history_table(sample_html)
    print(f"✓ Extracted {len(references)} deed references")
    
    # Print the first few references
    for i, ref in enumerate(references[:3]):
        print(f"\nDeed {i+1}:")
        print(f"  Book: {ref.get('book')}")
        print(f"  Page: {ref.get('page')}")
        print(f"  Date: {ref.get('date', 'N/A')}")
        print(f"  Year: {ref.get('year', 'N/A')}")
        print(f"  Grantor: {ref.get('grantor', 'N/A')}")
        print(f"  Grantee: {ref.get('grantee', 'N/A')}")
        if i == 2 and len(references) > 3:
            print(f"\n... and {len(references) - 3} more references")
    
    # Test extraction through main method
    print("\nTesting extract_deed_references:")
    all_refs = gemini.extract_deed_references(sample_html)
    print(f"✓ Extracted {len(all_refs)} deed references through main method")
    
    # Test deed batching process
    print("\nTesting process_deed_batches:")
    # Simulate some already collected deeds
    collected_deeds = [
        {"book": "W203", "page": "146"},
        {"book": "S111", "page": "290"}
    ]
    
    batches = gemini.process_deed_batches(sample_html, collected_deeds)
    print(f"✓ Total deeds: {batches['total_count']}")
    print(f"✓ Already collected: {batches['collected_count']}")
    print(f"✓ Pending collection: {batches['pending_count']}")
    
    # Test full workflow generation
    print("\nTesting generate_deed_collection_workflow:")
    workflow = gemini.generate_deed_collection_workflow("5590200072", all_refs, collected_deeds)
    
    print(f"✓ Generated workflow with {len(workflow['collection_sequence'])} deeds to collect")
    print("\nCollection sequence (first 3):")
    for i, seq in enumerate(workflow['collection_sequence'][:3]):
        print(f"  {i+1}. Book: {seq['book']}, Page: {seq['page']}")
    
    # Save results for inspection
    output_dir = Path("data/temp")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "deed_references.json", "w") as f:
        json.dump(references, f, indent=2)
        
    with open(output_dir / "deed_workflow.json", "w") as f:
        json.dump(workflow, f, indent=2)
        
    print(f"\n✓ Results saved to {output_dir}")
    
if __name__ == "__main__":
    test_sales_history_extraction()
