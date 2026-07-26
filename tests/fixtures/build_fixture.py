"""Helper that materializes the synthetic PLD fixture tree used by the
tests. Invoked by conftest.py into a tmp directory; kept as data-in-code
so the fixture is reviewable in one file."""

import os

CLASS_DIRTY = """<?xml version="1.0" encoding="utf-8"?>
<AxClass xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
  <Name>DemoDirtyClass</Name>
  <SourceCode>
    <Declaration><![CDATA[
class DemoDirtyClass extends RunBaseBatch
{
}
]]></Declaration>
    <Methods>
      <Method>
        <Name>doRawSql</Name>
        <Source><![CDATA[
public void doRawSql()
{
    Connection con = new Connection();
    Statement statement = con.createStatement();
    statement.executeUpdate("DELETE FROM CUSTTABLE");
}
]]></Source>
      </Method>
      <Method>
        <Name>updateRecord</Name>
        <Source><![CDATA[
public void updateRecord()
{
    CustTable custTable;
    ttsbegin;
    select forupdate custTable where custTable.AccountNum == '1';
    custTable.update();
    // TODO clean this up
    throw error("Something went wrong");
}
]]></Source>
      </Method>
      <Method>
        <Name>containerPlumbing</Name>
        <Source><![CDATA[
public container containerPlumbing(container _in)
{
    container result = conins(_in, 1, 'x');
    result = condel(result, 2, 1);
    return conpeek(result, 1);
}
]]></Source>
      </Method>
      <Method>
        <Name>interop</Name>
        <Source><![CDATA[
public void interop()
{
    new FileIOPermission('c:\\\\temp\\\\a.txt', 'r').assert();
    WinAPIServer::deleteFile('c:\\\\temp\\\\a.txt');
    System.IO.File::Delete('c:\\\\temp\\\\a.txt');
    infolog.add(Exception::Info, 'done');
}
]]></Source>
      </Method>
    </Methods>
  </SourceCode>
</AxClass>
"""

CLASS_CLEAN = """<?xml version="1.0" encoding="utf-8"?>
<AxClass xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
  <Name>DemoCleanClass</Name>
  <SourceCode>
    <Declaration><![CDATA[
class DemoCleanClass
{
}
]]></Declaration>
    <Methods>
      <Method>
        <Name>balancedTts</Name>
        <Source><![CDATA[
public void balancedTts()
{
    // the abort keyword counts as a legitimate closer; if only the
    // commit keyword were counted this would false-positive.
    ttsbegin;
    this.doWork();
    ttsabort;
}
]]></Source>
      </Method>
      <Method>
        <Name>formRefresh</Name>
        <Source><![CDATA[
public void formRefresh()
{
    // idiomatic datasource refresh; must NOT fire raw_sql_execute
    custTable_ds.executeQuery();
    container c = ['one declaration is fine'];
    throw error("@SYS12345");
}
]]></Source>
      </Method>
    </Methods>
  </SourceCode>
</AxClass>
"""

BROKEN = "<AxClass><Name>Broken"


def build(root: str) -> str:
    model_dir = os.path.join(root, "DemoPkg", "DemoModel", "AxClass")
    os.makedirs(model_dir)
    desc_dir = os.path.join(root, "DemoPkg", "Descriptor")
    os.makedirs(desc_dir)
    # A mirror dir that must be skipped.
    os.makedirs(os.path.join(root, "DemoPkg", "XppMetadata", "AxClass"))
    with open(os.path.join(model_dir, "DemoDirtyClass.xml"), "w",
              encoding="utf-8") as fh:
        fh.write(CLASS_DIRTY)
    with open(os.path.join(model_dir, "DemoCleanClass.xml"), "w",
              encoding="utf-8") as fh:
        fh.write(CLASS_CLEAN)
    with open(os.path.join(model_dir, "Broken.xml"), "w",
              encoding="utf-8") as fh:
        fh.write(BROKEN)
    return root
