"""Select an actual scoped realization, not an unscoped hidden source template."""
import unittest
from apply_copy import select_receipt_candidate

class Object(dict):type='MESH'

class Selection(unittest.TestCase):
    def test_same_receipt_template_and_member(self):
        record=dict(package_id='pkg',raw=dict(model_uid=10,geometry_uid=20),asset_sha256={'OrderedSix.fbx':'sha'},creation={'mesh':{'guid':'a'*32}})
        props=dict(unity_source_package_id='pkg',_vapb_fbx_source_asset_guid='a'*32,_vapb_fbx_source_asset_sha256='sha',
            _vapb_fbx_model_uid='10',_vapb_fbx_geometry_uid='20')
        template=Object(props);member=Object(props,_vapb_root_context_id='actual-root')
        result=select_receipt_candidate([template,member],record,'actual-root',lambda o:True)
        self.assertIs(result,member)
        with self.assertRaises(ValueError):select_receipt_candidate([template,member],record,'wrong-root',lambda o:True)
        with self.assertRaises(ValueError):select_receipt_candidate([template,member,Object(member)],record,'actual-root',lambda o:True)

if __name__=='__main__':unittest.main()
